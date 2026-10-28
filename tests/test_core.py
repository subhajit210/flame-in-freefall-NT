"""Run with:  python -m pytest"""
import numpy as np

from flame.assistant import check_citations, offline_answer
from flame.data import load_habitats, load_investigations, to_dataframe
from flame.evaluate import run as run_benchmark
from flame.importer import load_resources, match_columns, merge_tests
from flame.ranking import atmosphere_fit, coverage_gaps, rank
from flame.search import BM25, SearchIndex, rrf

RECORDS = load_investigations()
HABITATS = {h["id"]: h for h in load_habitats()}

MESSY_CSV = """Experiment;Sample material;Oxygen mole fraction;Pressure [kPa];Flow velocity (mm/s)
BASS-II;PMMA;0.17;101.3;50
BASS-II;PMMA;0.19;101.3;120
New Rover Test;Nomex;0.30;70.3;100
"""


def make_resources(folder):
    """A messy semicolon CSV, a text note and an unsupported file - like real-world downloads."""
    (folder / "messy_tests.csv").write_text(MESSY_CSV)
    (folder / "notes.txt").write_text("Water mist suppression was evaluated as a replacement for CO2 extinguishers.")
    (folder / "weird.xyz").write_text("unsupported")
    return load_resources(folder)


# ---------- data + ranking ----------
def test_dataset_loads_and_flattens():
    df = to_dataframe(RECORDS)
    assert len(df) == len(RECORDS) >= 15
    assert (df.o2_min <= df.o2_max).all()


def test_atmosphere_fit_is_one_inside_range_and_decays_outside():
    rec = {"conditions": {"o2_pct": [15, 25], "pressure_psi": [10, 15]}}
    assert atmosphere_fit(rec, {"o2_pct": 21, "pressure_psi": 14.7}) == 1.0
    near = atmosphere_fit(rec, {"o2_pct": 30, "pressure_psi": 14.7})
    far = atmosphere_fit(rec, {"o2_pct": 50, "pressure_psi": 14.7})
    assert 1.0 > near > far > 0


def test_rank_scores_bounded_and_sorted():
    ranked = rank(RECORDS, HABITATS["lunar_base"], {"prevention": 1, "detection": 1, "suppression": 1})
    assert ranked.score.between(0, 1).all() and ranked.score.is_monotonic_decreasing


def test_detection_priority_puts_smoke_studies_first():
    ranked = rank(RECORDS, HABITATS["iss"], {"prevention": 0, "detection": 3, "suppression": 0})
    assert ranked.iloc[0]["id"].startswith("SAME")


def test_lunar_solid_gap_is_detected():
    gaps = coverage_gaps(RECORDS, list(HABITATS.values()))
    row = gaps[(gaps.fuel_phase == "solid") & (gaps.habitat == HABITATS["lunar_base"]["name"])]
    assert row.iloc[0]["best_fit"] < 1


# ---------- search + assistant ----------
def test_bm25_prefers_rare_matching_words():
    assert BM25(["oxygen flame flame", "smoke detector particles", "oxygen oxygen"]).scores("smoke particles").argmax() == 1


def test_rrf_rewards_items_ranked_high_by_both():
    assert rrf([np.array([3.0, 2.0, 1.0]), np.array([1.0, 3.0, 2.0])]).argmax() == 1  # 2nd+1st beats 1st+3rd


def test_search_finds_relevant_record():
    hits = SearchIndex(RECORDS).search("smoke particle detector")
    assert hits and hits[0][0]["family"] == "SAME"


def test_offline_answer_mentions_ids():
    assert "[FLEX" in offline_answer("q", SearchIndex(RECORDS).search("extinguish droplet helium"))


def test_citation_guardrail_flags_unretrieved_ids():
    assert check_citations(f"ok [{RECORDS[0]['id']}] bad [Apollo-1]", [(RECORDS[0], 1.0)]) == ["apollo-1"]


def test_hybrid_beats_baseline_on_benchmark():
    res = run_benchmark()
    assert res["hybrid"]["mrr"] >= res["tfidf"]["mrr"] and res["hybrid"]["hit@3"] >= 0.9
    assert res["header_accuracy"] >= 0.9


# ---------- importer ----------
def test_messy_headers_are_matched():
    cols = match_columns(["Experiment", "Sample material", "Oxygen mole fraction", "Pressure [kPa]", "Flow velocity (mm/s)"])
    assert set(cols) == {"investigation", "fuel", "o2_pct", "pressure_psi", "flow_cm_s"}


def test_resources_load_with_unit_conversion_and_skip_unknown(tmp_path):
    res = make_resources(tmp_path)
    t = res["tests"]
    assert len(t) == 3
    assert t.o2_pct.max() == 30                        # fraction -> %
    assert abs(t.pressure_psi.iloc[0] - 14.69) < 0.05  # kPa -> psi
    assert t.flow_cm_s.max() == 12                     # mm/s -> cm/s
    assert any("water mist" in d["text"].lower() for d in res["documents"])
    assert [name for name, _ in res["skipped"]] == ["weird.xyz"]


def test_merge_updates_known_and_adds_new_investigations(tmp_path):
    merged = {r["id"]: r for r in merge_tests(RECORDS, make_resources(tmp_path)["tests"])}
    assert merged["BASS-II"]["conditions"]["o2_pct"] == [17.0, 19.0]
    assert merged["BASS-II"]["verified"] and merged["BASS-II"]["n_tests"] == 2
    assert "New Rover Test" in merged and len(merged) == len(RECORDS) + 1


def test_search_finds_document_passages(tmp_path):
    hits = SearchIndex(RECORDS, make_resources(tmp_path)["documents"]).search_docs("water mist extinguisher")
    assert hits and hits[0][0]["title"] == "notes.txt"
