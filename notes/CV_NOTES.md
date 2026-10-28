# CV_NOTES.md: everything you need for your CV and interviews

This is the single source for CV bullets, LinkedIn posts and interview prep. All numbers come from the code
(`python -m flame.evaluate` → the printed table). **If you change the data, rerun it and update the numbers here.**

---

## 1. One-liner

**Flame in Freefall** is an AI-assisted dashboard that ranks, compares and explains NASA's microgravity combustion experiments for
crew fire safety on the ISS, the Moon and Mars. It uses hybrid-retrieval RAG, a transparent ranking model, and an ingestion
pipeline that accepts any data format. Built for the NASA Space Apps Challenge 2026 (*"Flame in Freefall"* challenge).

## 2. Problem → solution

- **Problem:** decades of ISS fire experiments (BASS, Saffire, FLEX, ACME, SAME…) are scattered across NASA's PSI database.
  They are hard to find, compare, and relate to the future Moon base atmosphere (≥30% O₂ at ≤10.2 psi, which makes materials much more flammable).
- **Solution:**
  1. Rank experiments by relevance to a chosen habitat and safety goal (prevention / detection / suppression).
  2. Show which atmospheres have **no** test data.
  3. Answer questions in plain English with cited sources.
  4. Ingest NASA's resources in whatever format they arrive.

## 3. Tech stack

| Layer | Tools |
|---|---|
| Language | Python 3.12 |
| UI / deployment | Streamlit, Streamlit Community Cloud |
| Data | pandas, JSON, openpyxl (Excel), pypdf (PDF) |
| ML / IR | scikit-learn (TF-IDF, TruncatedSVD, cosine similarity), NumPy, BM25 written from scratch |
| GenAI | Google Gemini 2.5 Flash via `google-genai` SDK |
| Visualisation | Plotly |
| Quality | pytest (15 tests), evaluation harness, GitHub Actions CI |

## 4. Named techniques (what each one is, in one line)

| Technique | Where | One-line explanation |
|---|---|---|
| **Retrieval-Augmented Generation (RAG)** | `assistant.py` | The LLM answers only from retrieved records, which lowers hallucination risk |
| **Okapi BM25** (from scratch) | `search.py` | Keyword ranking with IDF weighting, term-frequency saturation (k1=1.5) and length normalisation (b=0.75) |
| **Latent Semantic Analysis (LSA)** | `search.py` | TF-IDF matrix → TruncatedSVD (16 latent dims), so related words match ("extinguish" ≈ "suppression") |
| **Reciprocal Rank Fusion (RRF)** | `search.py` | Merges rankings: `Σ 1/(60 + rank)`. No need to calibrate scores from different methods |
| **Hybrid sparse + dense-style retrieval** | `search.py` | Keyword precision (BM25) plus meaning-based recall (LSA) |
| **Citation-verification guardrail** | `assistant.py` | Regex-extracts `[citations]` from the LLM answer and flags any not in the retrieved set |
| **Graceful degradation** | `assistant.py` | No key or an API error → a deterministic offline answer. The app never breaks |
| **IR evaluation: Hit@k, MRR** | `flame/evaluate.py` | Standard search metrics on a hand-labelled benchmark, comparing 4 methods |
| **Fuzzy schema mapping + unit normalisation** | `importer.py` | Recognises messy headers by keyword and converts kPa/MPa/bar/atm→psi, mm/s and m/s→cm/s, fraction→% |
| **Text chunking** | `importer.py` | Splits documents into ~1500-character passages on line boundaries for retrieval |
| **Multi-criteria decision scoring** | `ranking.py` | Weighted sum of 4 normalised factors, with weights the user can change |
| **Exponential-decay envelope distance** | `ranking.py` | `exp(-√((ΔO₂/10)² + (ΔP/4)²))` measures how far you are extrapolating outside the tested conditions |
| **Coverage-gap analysis** | `ranking.py` | For each habitat × fuel type, the best available match. It exposes where no data exists |
| **Deterministic scoring with the LLM kept out of it** | design | The LLM explains results but never decides scores. That keeps scores auditable and reproducible |

## 5. Measured results (reproducible: `python -m flame.evaluate`)

**Retrieval:** 25 hand-labelled, paraphrased questions (labels fixed before running), 20 investigations.

| Method | Hit@1 | Hit@3 | MRR | ms/query |
|---|---|---|---|---|
| TF-IDF (baseline) | 80% | 100% | 0.893 | ~0.8 |
| BM25 | 92% | 100% | 0.960 | <0.1 |
| LSA | 96% | 96% | 0.970 | ~0.9 |
| **Hybrid (RRF)** | **96%** | **100%** | **0.980** | ~0.9 |

How to phrase these on a CV:
- MRR **0.89 → 0.98** (+10%) over the TF-IDF baseline
- Hit@1 **80% → 96%**, so top-1 misses fell from 5 to 1 out of 25 (**−80%**)
- Hybrid is the only method that is best on all three metrics: LSA alone drops Hit@3 to 96%, BM25 alone has Hit@1 of 92%
- About **1 ms** per query (measured 0.9–1.0 ms on a laptop; machine-dependent)

**Ingestion:**
- **9 verified file formats** (CSV, TSV, XLSX, JSON, PDF, DOCX, TXT, MD, HTML). `.xls` is also supported via `xlrd` but wasn't tested with a real file
- **5 pressure units**, **3 flow units**, O₂ given as a fraction or as %
- **100% of 40** messy header variants mapped correctly, including 7 that should be ignored

**Scope:**
- 20 ISS investigations across 6 hardware setups (CIR/ACME, CIR/MDCA, MSG, MSG + SPICE duct, Cygnus, handheld) and 5 fuel types
- 6 crew atmospheres, 5 dashboard tabs, 15 automated tests, CI on every push

**Key domain insight:** the planned Moon-base atmosphere (30% O₂, 10.2 psi) lies **outside every solid-material test in the
curated dataset** (all solid tests were at ≤21% O₂ and ~14.7 psi), even though fabrics and plastics are the main cabin fire load.
Only gas-burner tests (CFI-G, Flame Design, s-Flame, BRE) and liquid-droplet tests (FLEX, FLEX-2) went above 30% O₂.
⚠️ Re-check this against NASA PSI before stating it publicly. See section 10.

## 6. CV bullet points (final, one-line style)

**Main version: AI / GenAI / ML roles**

**Flame in Freefall | AI Fire-Safety Intelligence for Space Habitats** — Oct'26
*Built a RAG-powered dashboard for NASA Space Apps 2026 that ranks and interprets ISS combustion experiments for Moon and Mars fire safety*
- Engineered a **hybrid retrieval engine** fusing **BM25** and **LSA (TruncatedSVD)** via **Reciprocal Rank Fusion**, lifting **MRR from 0.89 to 0.98** over a TF-IDF baseline
- Grounded **Gemini** answers with a **RAG pipeline** and a **citation-verification guardrail**, layering a **deterministic ranking model** above LLM output for auditable scoring
- Built **format-agnostic ingestion** for **9 file formats** (PDF, DOCX, Excel, JSON) with **fuzzy schema mapping**, exposing that **no curated solid-material test covers the 30% O₂ lunar habitat**

**Data science variant**
- Designed a **multi-criteria scoring model** with **exponential-decay envelope distance** to rank **20 NASA experiments** against **6 crew atmospheres**
- Ran **coverage-gap analysis** on O₂/pressure test envelopes, revealing **no solid-material test data** in the curated set for the planned **30% O₂ / 10.2 psi** lunar habitat
- Benchmarked **4 retrieval methods** using **Hit@k** and **MRR**, with the **RRF hybrid** cutting top-1 misses by **80%** (Hit@1 **80% → 96%**)

**Software engineering variant**
- Implemented **Okapi BM25 from scratch** and fused it with **LSA** via **Reciprocal Rank Fusion**, reaching **0.98 MRR** at **~1 ms per query**
- Architected a modular **ingest → index → rank → generate** pipeline handling **9 file formats** and **5 pressure units**, with per-file **fault isolation**
- Shipped **15 pytest tests**, a reproducible **evaluation harness** and **GitHub Actions CI**, deployed on **Streamlit Cloud** with **graceful LLM fallback**

**Swap-in bullets** (use one in place of a weaker bullet if it fits the job better)
- Lifted **Hit@1 from 80% to 96%** on a hand-labelled benchmark, cutting top-1 retrieval misses by **80%**
- Added **graceful degradation** to an offline extractive mode, keeping the assistant usable with **zero API dependency**
- Normalised heterogeneous NASA data across **5 pressure units**, **3 flow units** and mole-fraction/percent O₂ into analysis-ready tables

**Rules:**
- Use one version per CV and don't mix numbers between versions.
- Add the live link and the GitHub link next to the title.
- If the team places in Space Apps, put it in the title line, e.g. `| Global Nominee`.
- Update the numbers if `python -m flame.evaluate` changes after adding NASA data.

## 7. What NOT to claim (stay defensible)

- ❌ "Trained an ML model" or "fine-tuned": the project uses classical IR (BM25, SVD) and an API LLM, not a trained model.
- ❌ "Large-scale data": 20 investigations. Scale isn't the point; retrieval quality and design are.
- ❌ "Vector database" or "neural embeddings": LSA is a classical latent-semantic method, not a neural embedding.
- ⚠️ The benchmark is **small (25 questions) and self-labelled**. Say so if asked. Labels were fixed before any run, and
  questions avoid the investigation names on purpose.
- ⚠️ The 40 header variants were also written by you, so treat 100% as "passes its own test suite", not a real-world accuracy figure.
- ⚠️ The seed condition values are approximate until checked against NASA PSI. Say "curated from NASA public descriptions".

## 8. Interview questions you should be ready for

| Question | Short answer |
|---|---|
| Why hybrid instead of only embeddings? | BM25 nails exact terms (fuel names, "Nomex"). LSA catches paraphrases. RRF combines them without score calibration. The benchmark shows hybrid is best on all three metrics |
| Why LSA instead of neural embeddings? | 20 records: no GPU, no API, no download, fully reproducible offline. Neural embeddings are the upgrade path at thousands of documents |
| What is MRR? | The average of 1/rank of the first correct result. 0.98 means the right answer is almost always ranked first |
| Why k=60 in RRF? | The standard constant from Cormack et al. (2009). It damps the dominance of top ranks so neither method overrules the other |
| How do you prevent hallucinations? | (1) RAG with only the top-k context, (2) an instruction to cite IDs, (3) a citation guardrail that flags unretrieved IDs, (4) low temperature |
| Why not let the LLM rank experiments? | It isn't reproducible or auditable. Safety decisions need a deterministic, explainable score, so the LLM only explains |
| How does the importer handle unknown formats? | Keyword header matching, unit detection from the header, per-file try/except, and unsupported files are listed, never fatal |
| How would you scale it? | Neural embeddings plus a vector index, LLM structured extraction from PDFs into records, and a bigger labelled benchmark |
| What did you find? | In the 20 curated investigations, every solid-material test was at ≤21% O₂ and sea-level pressure, so none covers the 30% O₂ / 10.2 psi lunar atmosphere. Newer tests such as Saffire-IV–VI may cover part of it, which is exactly what the tool is built to check |

## 9. Optional extensions (only if you want more)

- **LLM structured extraction:** Gemini reads PDF papers and fills investigation records using a JSON schema.
- **Tool-calling agent:** Gemini calls `rank()` / `coverage_gaps()` to answer "what's relevant for X?".
- **"Will it burn?" classifier:** logistic regression, if NASA data includes burn / no-burn outcomes.

## 10. Where every number comes from (read this before any interview)

There are three kinds of numbers, and you should never mix them up:
- **Measured:** produced by running code. You can rerun it and get the same value.
- **Counted:** a simple count of things in the repo (files, tests, formats…).
- **Chosen or sourced:** design constants you picked, or figures from NASA's challenge brief. **Never call these "results".**

### 10.1 Measured numbers (retrieval benchmark)

**How they were produced**
1. `tests/benchmark.json` holds **25 questions** written in plain language that deliberately avoid the investigation names
   (e.g. "How much carbon dioxide or helium is needed to put out burning fuel drops?" rather than "FLEX"). Each question lists the
   investigation id(s) that correctly answer it. **The labels were written before any search method was run**, so they weren't
   tuned to make one method look good.
2. `python -m flame.evaluate` runs every question through 4 methods and records **the position of the first correct
   investigation** in each ranked list.
3. From those positions it computes:
   - **Hit@1** = share of questions where the first result is correct.
   - **Hit@3** = share where a correct one appears in the top 3.
   - **MRR (Mean Reciprocal Rank)** = average of `1 / position`. First place scores 1, second 0.5, third 0.33, and so on.

**Worked example (say this in an interview)**

> Out of 25 questions, TF-IDF put the right answer first 20 times, second 4 times, and third once.
> Its MRR = (20×1 + 4×0.5 + 1×0.333) / 25 = 22.33 / 25 = **0.893**.
> The hybrid put it first 24 times and second once: (24×1 + 1×0.5) / 25 = 24.5 / 25 = **0.980**.

**Per-question evidence:** the only questions where any method missed first place. Each cell is the position of the first correct answer.

| Question | TF-IDF | BM25 | LSA | Hybrid |
|---|---|---|---|---|
| How big are smoke particles when cabin materials overheat? | 2 | 1 | 1 | 1 |
| Burning of fuel blends and neighbouring droplets | 3 | 1 | 1 | 1 |
| Improving smoke detectors for future spacecraft | 2 | 1 | 1 | 1 |
| Putting out fires on solids by diluting air with nitrogen | 2 | 2 | 4 | 2 |
| Which experiments help choose safer materials for crew vehicles? | 2 | 2 | 1 | 1 |
| *All other 20 questions* | 1 | 1 | 1 | 1 |

**What each CV number means:**

| CV number | Calculation | Plain meaning |
|---|---|---|
| **MRR 0.89 → 0.98** | 22.33/25 → 24.5/25 | On average the right experiment moved from "almost first" to "nearly always first" |
| **+10% MRR** | 0.980 / 0.893 = 1.097 | Relative improvement over the baseline |
| **Hit@1 80% → 96%** | 20/25 → 24/25 | Right answer ranked first in 24 of 25 questions instead of 20 |
| **Top-1 misses −80%** | misses 5 → 1, so (5−1)/5 = 80% | 4 of the 5 baseline mistakes were fixed |
| **Hit@3 = 100%** | 25/25 | The right answer was always in the top 3 for the hybrid |
| **~1 ms per query** | wall-clock time ÷ 25 | Measured 0.9–1.0 ms on a laptop. It varies by machine, so always say "about" |
| **4 methods** | TF-IDF, BM25, LSA, hybrid | Baseline, two single methods, and their fusion |

**Why the hybrid wins:** BM25 matches exact words; LSA matches related meanings. In the "safer materials" question, TF-IDF and BM25
ranked a smoke study first (those records also say "materials" a lot), while LSA picked up the topic. RRF combined both and got it
right. The hybrid is the only method that is best on all three metrics at once.

**Honest limits, if asked:**
- **Small and self-labelled.** 25 questions, labelled by you. It shows the methods' relative behaviour, not production-grade
  accuracy. A larger set labelled by others would be the next step.
- **Small collection.** 20 documents, so the absolute numbers are high for every method. The comparison between methods is
  what matters.
- **Deterministic.** SVD uses `random_state=0`, so anyone running the command gets exactly the same numbers.

### 10.2 Counted numbers (check them by looking)

| Number | What it counts | How to verify |
|---|---|---|
| **20 investigations** | Records in `data/investigations.json` | The Investigations metric on the dashboard |
| **6 crew atmospheres** | Earth, ISS/Orion, Moon base, 8.2 psi/34% exploration, Mars, spacesuit | `data/habitats.json` |
| **6 hardware setups** | CIR/ACME, CIR/MDCA, MSG, MSG + SPICE duct, Cygnus, handheld | Hardware metric on the dashboard |
| **5 fuel types** | solid, liquid, gas, smoke, dust | Data tab filter |
| **9 file formats** | CSV, TSV, XLSX, JSON, PDF, DOCX, TXT, MD, HTML | Each was loaded successfully in a manual check. `.xls` is supported but untested, so it isn't counted |
| **5 pressure units** | psi, kPa, MPa, bar, atm | `UNITS` in `flame/importer.py` |
| **3 flow units** | cm/s, mm/s, m/s | `UNITS` in `flame/importer.py` |
| **15 tests** | Functions in `tests/test_core.py` | `python -m pytest` prints "15 passed" |
| **40 header variants, 100%** | Messy column names in `tests/benchmark.json` | Printed by `python -m flame.evaluate`. **Keep this off the CV:** you wrote the variants, so it only proves the mapper passes its own test |

### 10.3 Chosen constants (design decisions, not results)

When asked "why this number?", the honest answer is "a reasonable, standard or tunable choice". Here's the justification for each:

| Constant | Value | Why |
|---|---|---|
| Ranking weights | 0.4 pillar, 0.3 atmosphere, 0.2 fuel, 0.1 gravity | Judgement: what the study is about matters most, then whether it tested the right atmosphere. **The user can change them with sidebar sliders**, so they aren't hidden assumptions |
| Atmosphere scales | 10 percentage points O₂, 4 psi | Roughly how far outside the tested range you can go before extrapolation becomes doubtful. 10 points outside gives a fit of `e⁻¹ ≈ 0.37` |
| Fuel relevance | solid 1.0, smoke 0.9, liquid 0.6, gas 0.5, dust 0.4 | Solids (fabrics, foam, wiring) are the main fire load in crew cabins, and smoke is what detectors see |
| Pillar scores 0–3 | per investigation | **Editorial judgement** from each experiment's stated objective. Be ready to justify any single score |
| BM25 k1 = 1.5, b = 0.75 | — | The standard defaults used in textbooks and search engines |
| RRF k = 60 | — | The constant from the original RRF paper (Cormack, Clarke & Büttcher, 2009) |
| LSA dims = 16 | — | Fewer than the 20 documents (SVD needs that), enough to keep topics apart |
| Chunk size 1500 characters | — | Big enough for a full paragraph of context, small enough to keep the Gemini prompt short |
| Gemini temperature 0.2 | — | Low randomness for factual answers |

### 10.4 Sourced numbers (from NASA, not from you)

| Number | Source | Note |
|---|---|---|
| **30% O₂ at 10.2 psi** for the Moon base / rover | The challenge brief ("likely 30% or greater, 10.2 psi or less") | NASA's planning figure, not something you derived |
| **"More than 40% more oxygen"** | Brief. Check: 30 / 20.9 = 1.435 → +43% | Say "over 40%", the brief's wording |
| **4.3 psi, 100% O₂** spacesuit; **14.7 psi** sea level | Brief | |
| **8.2 psi / 34% O₂** exploration atmosphere | NASA Exploration Atmospheres Working Group recommendation | Public NASA figure |
| **85% O₂** (highest tested, CFI-G) | Brief ("up to 85% oxygen") | |
| Per-investigation O₂ / pressure / flow ranges | **Approximate**, curated from public NASA descriptions | `"verified": false` until checked against PSI. Don't quote individual values as exact |

### 10.5 The key finding: exactly what you can claim

**What the code shows:** in `data/investigations.json`, every **solid** investigation (BASS, BASS-II, Saffire-I/II/III) has O₂ ≤ 21% and
pressure ≈ 14.7 psi. The Moon-base point (30%, 10.2 psi) is 9 points of O₂ and 4.5 psi away from that box, so its best atmosphere fit is
`exp(−√((9/10)² + (4.5/4)²)) ≈ 0.24`, shown in the Atmosphere gaps tab. Above 30% O₂ there are only gas-burner tests (CFI-G, Flame
Design, s-Flame, BRE) and liquid-droplet tests (FLEX, FLEX-2).

**Safe wording:** "In the curated set of 20 ISS investigations, no solid-material test covers the planned 30% O₂ / 10.2 psi lunar
atmosphere."

**Before you make it stronger** ("NASA has no data…"): check NASA PSI for **Saffire-IV, V and VI**, which reportedly tested
different oxygen and pressure conditions. If they cover it, the honest finding becomes "only the Saffire-IV–VI series covers it",
which is still a useful insight. The tool updates this automatically once their data is in `data/resources/`.

### 10.6 Re-checking every number yourself (2 minutes)

```bash
python -m pytest              # → 15 passed
python -m flame.evaluate      # → the Hit@1 / Hit@3 / MRR table + header accuracy
streamlit run app.py          # → Investigations 20, Hardware 6, Max O2 85%; Atmosphere gaps shows the 0.24 Moon/solid fit
```

If any number changes (after adding NASA data, for example), update sections 5, 6 and 10 here and the README table.

## 11. Prompt for generating new CV bullets with any LLM

Attach: `notes/CV_NOTES.md`, `README.md`, `docs/HOW_IT_WORKS.md` (+ fresh output of `python -m flame.evaluate`). Then paste:

> I'm attaching documentation for my project "Flame in Freefall". Write CV bullet points for a **[ROLE, e.g. GenAI engineer / data analyst / backend SWE]** role.
> Format: a title line, a one-line italic summary, then **[3]** bullets, each one line (~25 words), starting with a strong verb, with key techniques in **bold** and at least one number.
> Rules:
> 1. Use ONLY numbers from section 10 of CV_NOTES.md (measured or counted). Never invent or round up numbers.
> 2. Never present chosen constants (weights, k=60, etc.) or NASA-sourced figures as my results.
> 3. Respect section 7 "What NOT to claim" (no "trained a model", no "large-scale", no "vector database").
> 4. Keep the lunar finding scoped: "in the curated dataset", unless I tell you it's been verified against NASA PSI.
> 5. After the bullets, list each number you used and which line of section 10 it comes from.
> Give me **[N]** different versions emphasising **[e.g. retrieval / data engineering / product impact / NASA domain]**.
