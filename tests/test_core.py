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


# ---------- importer: real NASA PSI schema ----------
# Mirrors PSI-98 (Saffire-I): 'Material' not 'Sample Number' is the fuel, O2 is a text range, there is no
# investigation or pressure column, and the experiment name lives in the file name as 'SAFFIRE-1'.
PSI_CSV = (
    "Sample Number ,Material,Sample Thickness (cm),Air Flow (cm/s),Percent O2,Flow Direction \n"
    "S1,SIBAL Fabric,0.37,20,21.5 - 21.7,Concurrent\n"
    "S2,SIBAL Fabric,0.37,20,~ 21.5,Opposed\n"
    "F1C1/F1C2,Pre-test flow visualisation data,,,,\n"
)


def test_psi_fuel_column_beats_sample_number():
    cols = match_columns(["Sample Number ", "Material", "Sample Thickness (cm)", "Air Flow (cm/s)", "Percent O2"])
    assert cols["fuel"] == "Material"                       # 'material' outranks the weaker 'sample'
    assert cols["o2_pct"] == "Percent O2" and cols["flow_cm_s"] == "Air Flow (cm/s)"


def test_psi_text_ranges_parse_and_filename_maps_to_record(tmp_path):
    (tmp_path / "PSI-98_Experimental table_SAFFIRE-1.csv").write_text(PSI_CSV)
    t = load_resources(tmp_path)["tests"]
    assert len(t) == 2                                      # pre-test visualisation row (no numbers) dropped
    assert set(t["fuel"]) == {"SIBAL Fabric"}
    assert abs(t["o2_pct"].min() - 21.5) < 0.01 and abs(t["o2_pct"].max() - 21.6) < 0.01  # '21.5 - 21.7' -> 21.6

    merged = {r["id"]: r for r in merge_tests(RECORDS, t)}
    assert len(merged) == len(RECORDS)                      # mapped onto Saffire-I by file name, no new record
    s = merged["Saffire-I"]
    assert s["conditions"]["o2_pct"] == [21.5, 21.6]
    assert s["conditions"]["pressure_psi"] == [14.7, 14.7]  # kept: the PSI table has no pressure column
    assert s["verified"] and s["n_tests"] == 2


# PSI-69 (FLEX): non-UTF-8 file, pressure in mmHg, oxygen as an 'O ... mole fraction' column, a 0 = missing.
FLEX_CSV = (
    "FLEX Test #,Fuel,Ambient pressure; mmHg,O initial ambient composition; mole fraction,"
    "He initial ambient composition; mole fraction,Test end\n"
    "1,Methanol,760,0.21,0,Extinction\n"
    "2,Heptane,2320,0.34,0.1,Disruption–A\n"          # en-dash -> 0x96 byte in cp1252
    "3,Methanol,0,0.12,0,Extinction\n"
)


def test_psi_flex_encoding_units_and_mole_fraction(tmp_path):
    (tmp_path / "PSI-69_Experimental table_FLEX.csv").write_bytes(FLEX_CSV.encode("cp1252"))
    t = load_resources(tmp_path)["tests"]                   # must not crash on the non-UTF-8 byte
    assert len(t) == 3 and set(t["fuel"]) == {"Methanol", "Heptane"}
    assert t["o2_pct"].min() == 12 and t["o2_pct"].max() == 34    # mole fraction -> %
    assert abs(t["pressure_psi"].max() - 44.86) < 0.1            # mmHg -> psi
    assert t["pressure_psi"].isna().sum() == 1                   # the 0 mmHg row treated as missing

    flex = {r["id"]: r for r in merge_tests(RECORDS, t)}["FLEX"]
    assert flex["conditions"]["o2_pct"] == [12.0, 34.0]
    assert flex["verified"] and flex["n_tests"] == 3
