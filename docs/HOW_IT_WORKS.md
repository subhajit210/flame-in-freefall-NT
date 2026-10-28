# How it works: a code walkthrough

Read this when you want to understand or change the code. Each file is short and has one job.

## Data flow

```
data/investigations.json ─┐
                          ├─► flame/data.py: load_dataset() ─► records (list of dicts)
data/resources/*  ────────┘      uses flame/importer.py           │
   (CSV/Excel/JSON/PDF/…)        • tables  → test rows → update ranges
                                 • docs    → text passages
                                                                  ▼
                 flame/ranking.py  rank(), coverage_gaps()   → 🎯 Rank, 🗺️ Gaps tabs
                 flame/search.py   SearchIndex: BM25 + LSA → RRF   → 🤖 Ask tab (retrieval)
                 flame/assistant.py answer()  (Gemini or offline) + citation guardrail
                 app.py            Streamlit UI that calls all of the above
```

## Files

| File | What it does | Main functions |
|---|---|---|
| `app.py` | The whole UI: sidebar (habitat, priorities, weights) and 5 tabs. Holds no science logic. | — |
| `flame/data.py` | Loads the JSON files, validates records, flattens them into a DataFrame. | `load_dataset`, `validate`, `to_dataframe`, `record_text` |
| `flame/importer.py` | Reads any file in `data/resources/`, maps messy column names, converts units, merges test rows into records. | `load_resources`, `match_columns`, `merge_tests` |
| `flame/ranking.py` | The scoring model and the data-gap table. | `rank`, `atmosphere_fit`, `coverage_gaps` |
| `flame/search.py` | Hybrid search: BM25 + LSA, fused with Reciprocal Rank Fusion, over records and document passages. | `BM25`, `VectorRanker` (TF-IDF / LSA), `rrf`, `SearchIndex` |
| `flame/evaluate.py` | Benchmark: Hit@1/Hit@3/MRR for 4 retrieval methods plus column-mapping accuracy, using `tests/benchmark.json`. | `run`, `retrieval_metrics` |
| `flame/assistant.py` | Builds the context from search hits and asks Gemini, or writes the offline answer. | `answer`, `offline_answer` |
| `data/habitats.json` | Crew atmospheres (O₂ %, psi, g). | — |
| `tests/test_core.py` | 15 tests. Messy sample files for the importer are generated on the fly. | — |
| `tests/benchmark.json` | 25 labelled questions + 40 header variants used by `flame/evaluate.py`. | — |

## The record format (`data/investigations.json`)

```jsonc
{
  "id": "BASS-II", "name": "...", "family": "BASS", "hardware": "MSG (SPICE flow duct)", "year": 2014,
  "fuel_phase": "solid",              // solid | liquid | gas | smoke | dust | unknown
  "fuels": ["PMMA", ...], "sample_geometry": "...", "objective": "...",
  "conditions": {"o2_pct": [min, max], "pressure_psi": [min, max], "flow_cm_s": [min, max], "diluents": [...]},
  "variables": [...], "constants": [...], "measurements": [...], "key_findings": [...],
  "safety_pillars": {"prevention": 0-3, "detection": 0-3, "suppression": 0-3},
  "partial_gravity": 0-3, "earth_applications": [...],
  "verified": false                   // true once checked against / computed from NASA PSI data
}
```

## The ranking formula

For a habitat `h` and user priorities `p`:

- `pillar = Σ p_k · pillar_k / (3 · Σ p_k)`: how well the study matches what you care about
- `atmosphere = exp(-√((ΔO₂/10)² + (ΔP/4)²))`, where Δ is the distance from the habitat to the tested range (0 if inside)
- `fuel`: a fixed table (solid 1.0, smoke 0.9, liquid 0.6, gas 0.5, dust 0.4, unknown 0.5)
- `gravity`: 1 for a 0 g habitat, otherwise `partial_gravity / 3`
- `score = (0.4·pillar + 0.3·atmosphere + 0.2·fuel + 0.1·gravity) / Σweights`. You can change the weights in the sidebar.

## Common changes

| I want to… | Do this |
|---|---|
| Add an investigation by hand | Copy a block in `investigations.json` and edit it. |
| Use official data | Drop files in `data/resources/` (see `docs/GUIDE.md` Part B). |
| Recognise a new column name / unit | Add a word to `ALIASES` / `UNITS` in `flame/importer.py`. |
| Change the score | Edit `DEFAULT_WEIGHTS` / `FUEL_RELEVANCE` in `flame/ranking.py`. |
| Use another LLM (Groq, Claude…) | Replace the `try:` block in `flame/assistant.py::answer`. |
| Add a tab | Add a name to `st.tabs([...])` in `app.py` and a `with tab_x:` block. |

After any change, run `python -m pytest`. After changing search or data, also run `python -m flame.evaluate` and update the numbers in `README.md`.

## How hybrid search works (`flame/search.py`)

1. **BM25** scores each record by query words: rare words count more (IDF), repeating a word helps less and less (k1), and long
   records are not favoured (b).
2. **LSA** turns records into TF-IDF vectors, compresses them to 16 "topics" with TruncatedSVD, and compares the query by cosine
   similarity. Records with related wording match even without shared words.
3. **RRF** combines the two rankings: each record gets `1/(60 + rank)` from each method, summed. A record ranked well by both wins.
4. Collections with fewer than 3 passages skip LSA (SVD needs several documents) and use BM25 only.
