"""Load and validate the investigation and habitat datasets."""
import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESOURCES_DIR = DATA_DIR / "resources"  # drop official challenge files here
REQUIRED_FIELDS = ["id", "name", "family", "hardware", "year", "fuel_phase", "fuels",
                   "objective", "conditions", "measurements", "key_findings", "safety_pillars"]
RANGES = ("o2_pct", "pressure_psi", "flow_cm_s")


def _read(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def validate(records: list[dict]) -> None:
    """Fail fast with a clear message if a record is malformed."""
    ids = set()
    for r in records:
        missing = [k for k in REQUIRED_FIELDS if k not in r]
        if missing:
            raise ValueError(f"{r.get('id', '?')}: missing fields {missing}")
        if r["id"] in ids:
            raise ValueError(f"duplicate id {r['id']}")
        ids.add(r["id"])
        for key in RANGES:
            if r["conditions"][key][0] > r["conditions"][key][1]:
                raise ValueError(f"{r['id']}: {key} range is reversed")


def load_investigations() -> list[dict]:
    records = _read("investigations.json")["investigations"]
    validate(records)
    return records


def load_habitats() -> list[dict]:
    return _read("habitats.json")["habitats"]


def load_dataset() -> tuple[list[dict], dict]:
    """Seed investigations + anything in data/resources/ (test tables update condition ranges)."""
    from flame.importer import load_resources, merge_tests

    resources = load_resources(RESOURCES_DIR)
    records = merge_tests(load_investigations(), resources["tests"])
    validate(records)
    return records, resources


def to_dataframe(records: list[dict]) -> pd.DataFrame:
    """Flatten records into one row per investigation (tables, charts and CSV export)."""
    rows = []
    for r in records:
        c = r["conditions"]
        rows.append({
            **{k: r[k] for k in ("id", "name", "family", "hardware", "year", "fuel_phase")},
            "fuels": ", ".join(r["fuels"]),
            "o2_min": c["o2_pct"][0], "o2_max": c["o2_pct"][1],
            "p_min_psi": c["pressure_psi"][0], "p_max_psi": c["pressure_psi"][1],
            "flow_min_cm_s": c["flow_cm_s"][0], "flow_max_cm_s": c["flow_cm_s"][1],
            "diluents": ", ".join(c["diluents"]),
            **r["safety_pillars"],
            "partial_gravity": r.get("partial_gravity", 0),
            "measurements": ", ".join(r["measurements"]),
            "verified": r.get("verified", False),
            "n_tests": r.get("n_tests", 0),
        })
    return pd.DataFrame(rows)


def record_text(r: dict) -> str:
    """All searchable text of one record, used by search and the AI assistant."""
    c = r["conditions"]
    lists = [r["fuels"], r.get("variables", []), r["measurements"], r["key_findings"], r.get("earth_applications", [])]
    return " ".join([
        r["id"], r["name"], r["family"], r["hardware"], r["fuel_phase"], r.get("sample_geometry", ""), r["objective"],
        *(" ".join(x) for x in lists),
        f"oxygen {c['o2_pct'][0]}-{c['o2_pct'][1]} percent",
        f"pressure {c['pressure_psi'][0]}-{c['pressure_psi'][1]} psi",
        f"flow {c['flow_cm_s'][0]}-{c['flow_cm_s'][1]} cm/s",
        "diluents " + " ".join(c["diluents"]),
    ])
