# Submission: Flame in Freefall

NASA Space Apps Challenge 2026 - "Flame in Freefall".

- Live app: https://flame-in-freefall-nt-duqfaa7frygufkrorlvwfc.streamlit.app
- Source code: https://github.com/subhajit210/flame-in-freefall-NT

## One-line summary

A decision-support dashboard that turns decades of NASA microgravity combustion experiments into fire-safety
answers for crew habitats, using hybrid retrieval and retrieval-augmented generation over NASA's own data.

## Problem

NASA has run combustion experiments aboard the ISS for over twenty years (BASS, Saffire, FLEX, ACME, SAME). The
results live in the Physical Science Informatics (PSI) repository, but they differ in fuels, hardware, atmospheres
and measurements, which makes them hard to locate and compare. The question is pressing for planned lunar habitats,
which are expected to run at roughly 30% oxygen and 10.2 psi to shorten spacesuit pre-breathe - an atmosphere in
which materials are considerably more flammable, and for which it is not obvious which existing tests still apply.

## What it does

Pick a crew habitat and a fire-safety priority (prevention, detection, suppression); the dashboard then:

1. **Rank** - scores every investigation for that habitat with a transparent, adjustable model.
2. **Atmosphere gaps** - maps the oxygen and pressure each experiment actually tested against crew atmospheres, and
   flags where no test data exists.
3. **Compare** - puts two to four investigations side by side.
4. **Ask** - answers plain-English questions from retrieved records, with cited sources.
5. **Data** - a filterable, exportable table that also ingests real NASA data files dropped into the project.

## How it works (tech)

- **Hybrid retrieval**: Okapi BM25 (implemented from scratch) for exact terms + Latent Semantic Analysis (TF-IDF
  reduced with truncated SVD) for related terminology, fused with Reciprocal Rank Fusion.
- **Retrieval-augmented generation**: the top records are sent to Google Gemini with an instruction to answer only
  from that context and cite investigation IDs; a citation guardrail flags any citation not in the retrieved set,
  and an offline extractive answer is returned when no API key is present.
- **Transparent ranking**: a weighted score over pillar fit, atmosphere fit (exponential-decay distance from the
  tested envelope), fuel relevance and gravity fit - deterministic and independent of the language model.
- **Robust ingestion pipeline**: reads messy real NASA tables (varied encodings, units such as mmHg and kPa,
  mole-fraction oxygen, text ranges), maps columns by keyword, and matches PSI file names to dataset records.
- **Evaluation**: a labelled benchmark reports Hit@k and MRR; the fused method reaches MRR 0.98 and is best on all
  three metrics. 18 unit tests run in CI on every push.

## Data

Investigation records were compiled from public NASA descriptions and are clearly labelled approximate until checked
against PSI. Real NASA PSI Experimental Tables (CC0-1.0) are ingested at load time: PSI-98 (Saffire-I) and PSI-69
(FLEX) replace those records' conditions with measured values. Each PSI investigation has a citable DOI on its
repository page.

## Key result

In the current data, every solid-material test (BASS, Saffire) sits at or below 21% oxygen near sea-level pressure.
None covers the projected lunar-habitat atmosphere, even though solid materials are the main cabin fire load - which
points to where new experiments matter most.

## How to run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Optional: add a Gemini API key to `.streamlit/secrets.toml` for generated answers in the Ask tab.

## AI use

Google Gemini is used inside the application to generate answers in the Ask tab (constrained to retrieved context
with a citation check). AI coding assistance was used during development.

## 60-second demo script

1. (10s) Problem: NASA has decades of ISS fire experiments, but they are scattered and the Moon base will run far
   richer in oxygen than Earth air.
2. (15s) Rank: select Moon Base, move the priority sliders, show the ranking respond.
3. (15s) Atmosphere gaps: show the crew-atmosphere stars sitting outside the solid-material test boxes, and the
   warning. State the key finding.
4. (10s) Compare: two investigations side by side.
5. (10s) Ask: type a question, show the cited answer.
6. (5s) Close: drop in new NASA data in any format and the dashboard updates automatically.
