# 🔥 Flame in Freefall

![tests](https://github.com/<your-username>/flame-in-freefall/actions/workflows/tests.yml/badge.svg)

**NASA Space Apps Challenge 2026: an AI-assisted dashboard of fire-safety insights from microgravity combustion data**

Since the 2000s NASA has flown many combustion experiments on the ISS (BASS, Saffire, FLEX, ACME, SAME…). The results sit in NASA's
Physical Science Informatics (PSI) database, but they are hard to find, compare and interpret. This dashboard **ranks, compares
and explains** those investigations for a chosen crew habitat, such as the ISS, a Moon base at 30% O₂ / 10.2 psi, or Mars. It also
shows **where the data runs out**.

## Features

| Tab | What it does |
|---|---|
| 🎯 **Rank** | Scores every investigation for the selected habitat and safety priority (prevention / detection / suppression). The score is transparent and can be tuned. |
| 🗺️ **Atmosphere gaps** | Plots each experiment's tested O₂ and pressure range against the crew atmospheres, and flags habitats with no test data. |
| ⚖️ **Compare** | Shows 2–4 investigations side by side: conditions, measurements, shared variables, and a radar chart of safety relevance. |
| 🤖 **Ask** | Plain-English questions answered by Gemini from retrieved NASA records, with citations checked by a guardrail. Works offline without a key. |
| 📄 **Data** | Filterable table, CSV export for modelling, imported resource files, and full details per investigation. |

**Key finding:** the planned Moon-base atmosphere (30% O₂, 10.2 psi) lies outside every solid-material microgravity test, even
though fabrics and plastics are the main fire load in a cabin.

## How it works

1. **Hybrid retrieval** (`flame/search.py`): **BM25** keyword ranking plus **LSA** (TF-IDF reduced with TruncatedSVD, which
   matches on meaning), merged with **Reciprocal Rank Fusion**.
2. **RAG assistant** (`flame/assistant.py`): only the retrieved records go to Gemini, which must cite them. A **citation
   guardrail** flags any citation that wasn't retrieved. Without an API key it falls back to an offline answer.
3. **Ranking model** (`flame/ranking.py`): `score = 0.4·pillar + 0.3·atmosphere + 0.2·fuel + 0.1·gravity`, where atmosphere fit is
   `exp(-distance)` from the habitat's (O₂, pressure) to each tested range. The LLM never sets scores.
4. **Any-format ingestion** (`flame/importer.py`): CSV, TSV, Excel, JSON, PDF, DOCX, TXT, MD and HTML. Messy column names are
   matched and units converted. Test tables update the condition ranges, and documents become searchable.

Full code walkthrough: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

## Measured results

`python -m flame.evaluate` on 25 hand-labelled, paraphrased questions:

| Retrieval method | Hit@1 | Hit@3 | MRR |
|---|---|---|---|
| TF-IDF (baseline) | 80% | 100% | 0.893 |
| BM25 | 92% | 100% | 0.960 |
| LSA | 96% | 96% | 0.970 |
| **Hybrid BM25 + LSA (RRF)** | **96%** | **100%** | **0.980** |

The column mapper recognises 100% of 40 messy header variants. All 15 tests run on every push through GitHub Actions.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. Run the tests with `python -m pytest`.

For the optional AI answers, get a free Gemini API key at https://aistudio.google.com/apikey and put it in
`.streamlit/secrets.toml` as `GEMINI_API_KEY = "..."`. Step-by-step instructions, including Streamlit Cloud, are in
[docs/GUIDE.md](docs/GUIDE.md) step A4. To add NASA data, drop files into `data/resources/` and click **Reload**.

Step-by-step instructions for running, testing, adding NASA data and deploying: **[docs/GUIDE.md](docs/GUIDE.md)**.

## Project structure

```
flame-in-freefall/
├── app.py                  Streamlit dashboard (5 tabs)
├── requirements.txt
├── flame/                  core logic
│   ├── data.py             load + validate the JSON data
│   ├── importer.py         any-format ingestion: tables + documents
│   ├── search.py           hybrid retrieval: BM25 + LSA + RRF
│   ├── assistant.py        Gemini RAG + citation guardrail + offline fallback
│   ├── ranking.py          relevance score + coverage-gap analysis
│   └── evaluate.py         retrieval benchmark (Hit@k, MRR)
├── data/
│   ├── investigations.json 20 ISS combustion investigations
│   ├── habitats.json       6 crew atmospheres
│   └── resources/          ← drop official NASA files here
├── tests/
│   ├── test_core.py        15 tests
│   └── benchmark.json      labelled questions for evaluate.py
└── docs/
    ├── GUIDE.md            run, test, add data, deploy
    └── HOW_IT_WORKS.md     code walkthrough
```

## Data note

`data/investigations.json` was curated from public NASA descriptions. Condition ranges and years are approximate
(`"verified": false`) until checked against NASA PSI (https://psi.ssl.nasa.gov). Records updated from imported test data are
marked `verified`.
