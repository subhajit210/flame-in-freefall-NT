# Flame in Freefall

![tests](https://github.com/<your-username>/flame-in-freefall/actions/workflows/tests.yml/badge.svg)

A decision-support dashboard that organises NASA's microgravity combustion experiments for spacecraft and habitat fire safety.
Developed for the NASA Space Apps Challenge 2026 ("Flame in Freefall").

## Motivation

NASA has conducted combustion experiments aboard the International Space Station for more than two decades. These include BASS,
Saffire, FLEX, ACME and SAME. Their results are published through the Physical Science Informatics (PSI) system, but the
investigations differ in fuels, hardware, atmospheres and measurements, which makes them difficult to locate and compare.

The question becomes more pressing with planned lunar habitats. To shorten spacesuit pre-breathe, the Moon base and pressurized
rovers are expected to operate at roughly 30% oxygen and 10.2 psi, compared with 20.9% oxygen and 14.7 psi on Earth. Materials are
considerably more flammable in that atmosphere, and it is not obvious which existing experiments remain applicable.

This project addresses three questions for a chosen crew environment:

1. Which investigations are most relevant to its fire-safety needs?
2. Which atmospheric conditions are covered by existing test data, and which are not?
3. What do the investigations report on a given topic, with sources?

## Functionality

The application is a Streamlit dashboard with five views:

| View | Description |
|---|---|
| Rank | Scores all investigations for a selected habitat and safety priority (prevention, detection, suppression). Weights are user-adjustable. |
| Atmosphere gaps | Plots each investigation's tested oxygen and pressure range against crew atmospheres, and reports coverage per fuel type. |
| Compare | Side-by-side comparison of two to four investigations: conditions, measurements, shared variables. |
| Ask | Natural-language questions answered from retrieved investigation records, with citations. |
| Data | Filterable table with CSV export, imported resource files, and per-investigation detail. |

## Method

### Retrieval

Investigation records and imported documents are indexed with two complementary methods:

- **Okapi BM25** (k1 = 1.5, b = 0.75), implemented directly, for exact term matching.
- **Latent Semantic Analysis**: TF-IDF vectors reduced to 16 dimensions with truncated SVD, compared by cosine similarity, which
  matches related terminology.

The two rankings are combined with **Reciprocal Rank Fusion** (k = 60), which merges ranks rather than raw scores and so needs no
score calibration.

### Question answering

The top-ranked records are passed to Google Gemini with an instruction to answer only from that context and to cite investigation
identifiers. Each citation in the response is then checked against the retrieved set, and any citation not in it is flagged. If no
API key is configured, or the request fails, the system returns an extractive summary of the retrieved records.

### Relevance ranking

Ranking is deterministic and independent of the language model. For a habitat *h* and investigation *i*:

```
score = 0.4 · pillar + 0.3 · atmosphere + 0.2 · fuel + 0.1 · gravity

atmosphere = exp( -sqrt( (ΔO2 / 10)² + (ΔP / 4)² ) )
```

- ΔO2 (percentage points) and ΔP (psi) are the distances from the habitat's atmosphere to the investigation's tested range, and are
  zero inside it.
- *pillar* reflects the user's prevention, detection and suppression priorities.
- *fuel* reflects how representative the fuel is of cabin fire loads.
- *gravity* rewards investigations that inform partial-gravity conditions.

All terms lie in [0, 1].

### Data ingestion

Files placed in `data/resources/` are loaded automatically:

- **Tables** (CSV, TSV, Excel, JSON): column names are matched by keyword, and pressure (kPa, MPa, bar, atm) and flow (mm/s, m/s)
  are converted to psi and cm/s. Per-test rows replace each investigation's condition ranges with the measured minimum and maximum.
- **Documents** (PDF, DOCX, TXT, Markdown, HTML): split into passages and added to the retrieval index.

Unreadable files are reported rather than causing failure.

## Evaluation

Retrieval was evaluated on 25 natural-language questions that avoid investigation names. Each is labelled with the investigation(s)
that answer it, and the labels were fixed before any method was run. Reported metrics are Hit@k (the share of questions with a
correct investigation in the top *k*) and Mean Reciprocal Rank.

| Method | Hit@1 | Hit@3 | MRR |
|---|---|---|---|
| TF-IDF (baseline) | 0.80 | 1.00 | 0.893 |
| BM25 | 0.92 | 1.00 | 0.960 |
| LSA | 0.96 | 0.96 | 0.970 |
| BM25 + LSA (RRF) | 0.96 | 1.00 | 0.980 |

The fused method is the only one that is best on all three metrics. The benchmark is small and was labelled by the author, so the
results indicate the methods' relative behaviour rather than absolute accuracy. Results are deterministic and can be reproduced
with `python -m flame.evaluate`.

## Observation

In the current dataset, all solid-material investigations (BASS, BASS-II, Saffire-I to III) were conducted at or below 21% oxygen
and near sea-level pressure. None therefore covers the projected lunar habitat atmosphere, although solid materials such as fabrics,
foams and wiring make up most of a cabin's fire load. Tests above 30% oxygen in the dataset used gaseous or liquid fuels only. This
observation is limited to the curated dataset and should be re-examined as PSI data, including later Saffire flights, is added.

## Installation

Requires Python 3.11 to 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The application opens at http://localhost:8501.

To enable generated answers, create `.streamlit/secrets.toml` containing `GEMINI_API_KEY = "..."`. A free key is available from
Google AI Studio. Without a key, all other functionality is unaffected.

Tests and evaluation:

```bash
python -m pytest
python -m flame.evaluate
```

Detailed instructions for setup, adding NASA data, deployment and troubleshooting are in [docs/GUIDE.md](docs/GUIDE.md). A
description of the code is in [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

## Repository structure

```
app.py                     Streamlit application
flame/
    data.py                dataset loading and validation
    importer.py            ingestion of tables and documents
    search.py              BM25, LSA and rank fusion
    assistant.py           retrieval-augmented answering and citation check
    ranking.py             relevance scoring and coverage analysis
    evaluate.py            retrieval benchmark
data/
    investigations.json    20 ISS combustion investigations
    habitats.json          6 reference crew atmospheres
    resources/             input folder for NASA data files
tests/
    test_core.py           unit tests
    benchmark.json         labelled evaluation questions
docs/                      user guide and code walkthrough
```

## Data and limitations

- `data/investigations.json` was compiled from public NASA descriptions of each investigation. Test condition ranges and years are
  approximate and are marked `"verified": false` until checked against PSI. Records updated from imported test data are marked as
  verified.
- Relevance scores per safety pillar (0–3) are editorial assessments based on each investigation's stated objectives.
- PSI does not yet contain partial-gravity combustion data. The E-FIELD investigation, which uses electric fields to mimic buoyancy,
  is the closest available proxy.

## References

- NASA Physical Science Informatics: https://psi.ssl.nasa.gov
- Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance Framework: BM25 and Beyond. *Foundations and Trends in
  Information Retrieval*, 3(4).
- Deerwester, S., et al. (1990). Indexing by Latent Semantic Analysis. *Journal of the American Society for Information Science*,
  41(6).
- Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning
  Methods. *Proceedings of SIGIR 2009*.
