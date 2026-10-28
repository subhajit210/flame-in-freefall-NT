# Technical Overview

This document describes the code structure, data model and algorithms. Each module has a single responsibility, and none
exceeds about 200 lines.

## Data flow

```
data/investigations.json ──┐
                           ├──> flame/data.py: load_dataset() ──> investigation records
data/resources/* ──────────┘       uses flame/importer.py
                                     tables    -> test rows -> updated condition ranges
                                     documents -> text passages

records ──> flame/ranking.py     rank(), coverage_gaps()       -> Rank, Atmosphere gaps views
        ──> flame/search.py      BM25 + LSA, fused by RRF      -> Ask view (retrieval)
        ──> flame/assistant.py   Gemini answer + citation check, or extractive fallback
app.py: Streamlit interface that calls the modules above
```

## Modules

| File | Responsibility | Main functions |
|---|---|---|
| `app.py` | User interface: sidebar controls and five views. Contains no analysis logic. | — |
| `flame/data.py` | Loads and validates the JSON datasets; flattens records into a DataFrame. | `load_dataset`, `validate`, `to_dataframe`, `record_text` |
| `flame/importer.py` | Reads files in `data/resources/`, maps column names, converts units, merges test rows into records. | `load_resources`, `match_columns`, `merge_tests` |
| `flame/search.py` | BM25 and LSA retrieval over records and document passages, combined with Reciprocal Rank Fusion. | `BM25`, `VectorRanker`, `rrf`, `SearchIndex` |
| `flame/assistant.py` | Builds the prompt from retrieved items, calls Gemini, checks citations; extractive fallback. | `answer`, `offline_answer`, `check_citations` |
| `flame/ranking.py` | Relevance scoring and atmosphere coverage analysis. | `rank`, `atmosphere_fit`, `coverage_gaps` |
| `flame/evaluate.py` | Retrieval benchmark (Hit@1, Hit@3, MRR) and column-mapping accuracy. | `run`, `retrieval_metrics` |
| `data/habitats.json` | Reference crew atmospheres: oxygen fraction, pressure, gravity. | — |
| `tests/test_core.py` | Unit tests. Importer test files are generated at runtime. | — |
| `tests/benchmark.json` | 25 labelled questions and 40 header variants used by `flame/evaluate.py`. | — |

## Record schema

Each entry in `data/investigations.json` has the following fields:

```jsonc
{
  "id": "BASS-II", "name": "...", "family": "BASS", "hardware": "MSG (SPICE flow duct)", "year": 2014,
  "fuel_phase": "solid",              // solid | liquid | gas | smoke | dust | unknown
  "fuels": ["PMMA", ...], "sample_geometry": "...", "objective": "...",
  "conditions": {"o2_pct": [min, max], "pressure_psi": [min, max], "flow_cm_s": [min, max], "diluents": [...]},
  "variables": [...], "constants": [...], "measurements": [...], "key_findings": [...],
  "safety_pillars": {"prevention": 0-3, "detection": 0-3, "suppression": 0-3},
  "partial_gravity": 0-3, "earth_applications": [...],
  "verified": false                   // true once checked against, or derived from, PSI data
}
```

`validate()` checks that required fields are present, that identifiers are unique, and that no range is reversed.

## Relevance ranking

For habitat *h* and user priorities *p* (each 0–3):

| Term | Definition |
|---|---|
| pillar | `Σ p_k · pillar_k / (3 · Σ p_k)`: agreement between the investigation's focus and the user's priorities |
| atmosphere | `exp(-sqrt((ΔO2/10)² + (ΔP/4)²))`, where ΔO2 and ΔP are distances from the habitat to the tested range (zero inside it) |
| fuel | Fixed relevance by fuel type: solid 1.0, smoke 0.9, liquid 0.6, gas 0.5, dust 0.4, unknown 0.5 |
| gravity | 1 for microgravity habitats; otherwise `partial_gravity / 3` |

```
score = (0.4 · pillar + 0.3 · atmosphere + 0.2 · fuel + 0.1 · gravity) / Σ weights
```

The weights are defaults and can be adjusted in the sidebar.

`coverage_gaps()` reports, for each habitat and fuel type, the highest atmosphere fit among matching investigations. A value of 1.0
means at least one investigation tested that exact atmosphere.

## Retrieval

1. **BM25** scores documents by query terms. Rare terms receive higher weight (inverse document frequency), repeated terms
   contribute with diminishing returns (k1 = 1.5), and longer documents are normalised (b = 0.75).
2. **LSA** represents documents as TF-IDF vectors, reduces them to 16 latent dimensions with truncated SVD, and ranks by cosine
   similarity, so documents using related terminology can match without shared words.
3. **Reciprocal Rank Fusion** combines the two rankings. Each document receives `1 / (60 + rank)` from each method, and the
   contributions are summed.
4. Collections with fewer than three passages use BM25 only, since SVD requires several documents.

`VectorRanker` without SVD provides the plain TF-IDF baseline used in the evaluation.

## Answer generation

1. The top five investigation records and top three document passages are serialised as JSON context.
2. Gemini receives a system instruction to answer only from that context and to cite identifiers in square brackets (temperature 0.2).
3. `check_citations()` extracts every bracketed citation and flags any that does not match a retrieved identifier or document title.
4. If no key is configured, or the request fails, `offline_answer()` returns the retrieved records with objectives and key findings.

## Ingestion

- **Tables:** `match_columns()` assigns each standard field (investigation, fuel, oxygen, pressure, flow, objective) to the first
  column whose normalised header contains one of its keywords. `unit_factor()` reads the unit from the header and converts to psi
  and cm/s. Oxygen values of at most 1 are treated as mole fractions.
- **Merging:** `merge_tests()` groups rows by investigation, matches them to existing records by identifier or name (ignoring case
  and punctuation), and replaces condition ranges with the observed minimum and maximum. Unmatched names create new records.
- **Documents:** text is extracted (pypdf for PDF, the XML body for DOCX, tag stripping for HTML) and split into passages of about
  1,500 characters on line boundaries.
- **Failures:** each file is processed independently. Errors are recorded and shown in the Data view.

## Common modifications

| Task | Location |
|---|---|
| Add an investigation | Copy an existing record in `data/investigations.json` |
| Import official data | Place files in `data/resources/` (see `docs/GUIDE.md`, section 3) |
| Recognise a new header or unit | `ALIASES` or `UNITS` in `flame/importer.py` |
| Change scoring | `DEFAULT_WEIGHTS` or `FUEL_RELEVANCE` in `flame/ranking.py` |
| Use a different language model | The `try` block in `answer()` in `flame/assistant.py` |
| Add a view | Add a label to `st.tabs([...])` in `app.py` and a corresponding `with` block |

After any change, run `python -m pytest`. After changes to retrieval or data, also run `python -m flame.evaluate` and update the
results table in `README.md`.
