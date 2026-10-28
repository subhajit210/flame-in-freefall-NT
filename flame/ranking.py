"""Transparent relevance ranking of investigations for a target crew habitat.

score = w_pillar * pillar_fit      (does it study what you care about: prevention / detection / suppression?)
      + w_atm    * atmosphere_fit  (were tests run near the habitat's O2 % and pressure?)
      + w_fuel   * fuel_fit        (how representative is the fuel of real cabin fire hazards?)
      + w_grav   * gravity_fit     (how well does it inform the habitat's gravity level?)
Every term is in [0, 1], so the total is in [0, 1] when the weights sum to 1.
"""
import math

import pandas as pd

# How representative each fuel type is of fires in a crew cabin (solids = clothing, foam, wiring, etc.).
FUEL_RELEVANCE = {"solid": 1.0, "smoke": 0.9, "liquid": 0.6, "gas": 0.5, "dust": 0.4, "unknown": 0.5}

# Scales used to turn "distance outside the tested range" into a 0-1 score.
O2_SCALE_PCT = 10.0      # 10 percentage points outside the range -> score ~0.37
PRESSURE_SCALE_PSI = 4.0

DEFAULT_WEIGHTS = {"pillar": 0.4, "atmosphere": 0.3, "fuel": 0.2, "gravity": 0.1}


def _gap(value: float, lo: float, hi: float) -> float:
    """Distance from value to the [lo, hi] interval (0 if inside)."""
    return max(0.0, lo - value, value - hi)


def atmosphere_fit(record: dict, habitat: dict) -> float:
    c = record["conditions"]
    d_o2 = _gap(habitat["o2_pct"], *c["o2_pct"]) / O2_SCALE_PCT
    d_p = _gap(habitat["pressure_psi"], *c["pressure_psi"]) / PRESSURE_SCALE_PSI
    return math.exp(-math.hypot(d_o2, d_p))


def pillar_fit(record: dict, priorities: dict) -> float:
    """Weighted average of the 0-3 pillar scores using the user's priorities."""
    total = sum(priorities.values()) or 1.0
    s = sum(record["safety_pillars"][k] * v for k, v in priorities.items())
    return s / (3.0 * total)


def gravity_fit(record: dict, habitat: dict) -> float:
    # All PSI combustion data is microgravity, so it fully informs 0 g habitats.
    # For partial / normal gravity, investigations that mimic or bound buoyancy count more.
    if habitat["gravity_g"] == 0:
        return 1.0
    return record.get("partial_gravity", 0) / 3.0


def explain(record: dict, habitat: dict) -> str:
    """One-line, human-readable reason for the atmosphere score."""
    c = record["conditions"]
    o2_lo, o2_hi = c["o2_pct"]
    p_lo, p_hi = c["pressure_psi"]
    notes = []
    if o2_lo <= habitat["o2_pct"] <= o2_hi:
        notes.append(f"O2 {habitat['o2_pct']:g}% inside tested {o2_lo}-{o2_hi}%")
    else:
        notes.append(f"O2 tested {o2_lo}-{o2_hi}% vs target {habitat['o2_pct']:g}% (extrapolation)")
    if p_lo <= habitat["pressure_psi"] <= p_hi:
        notes.append(f"pressure covered")
    else:
        notes.append(f"pressure tested {p_lo}-{p_hi} psi vs {habitat['pressure_psi']:g} psi")
    return "; ".join(notes)


def rank(records: list[dict], habitat: dict, priorities: dict, weights: dict | None = None) -> pd.DataFrame:
    w = weights or DEFAULT_WEIGHTS
    w_sum = sum(w.values()) or 1.0
    rows = []
    for r in records:
        parts = {
            "pillar": pillar_fit(r, priorities),
            "atmosphere": atmosphere_fit(r, habitat),
            "fuel": FUEL_RELEVANCE.get(r["fuel_phase"], 0.5),
            "gravity": gravity_fit(r, habitat),
        }
        score = sum(w[k] * parts[k] for k in parts) / w_sum
        rows.append({"id": r["id"], "name": r["name"], "fuel_phase": r["fuel_phase"],
                     "score": round(score, 3), **{k: round(v, 2) for k, v in parts.items()},
                     "why": explain(r, habitat)})
    return pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)


def coverage_gaps(records: list[dict], habitats: list[dict]) -> pd.DataFrame:
    """For each habitat and fuel phase: does any investigation cover its atmosphere?"""
    rows = []
    for h in habitats:
        for phase in sorted({r["fuel_phase"] for r in records}):
            group = [r for r in records if r["fuel_phase"] == phase]
            best = max(group, key=lambda r: atmosphere_fit(r, h))
            rows.append({"habitat": h["name"], "fuel_phase": phase,
                         "best_fit": round(atmosphere_fit(best, h), 2), "best_investigation": best["id"]})
    return pd.DataFrame(rows)
