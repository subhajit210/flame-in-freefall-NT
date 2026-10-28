# HANDOFF (private): project state, next steps, submission

_Last updated: 2026-10-29_

## Current state ✅

- Streamlit dashboard with 5 working tabs: Rank, Atmosphere gaps, Compare, Ask, Data.
- 20 curated investigations (BASS, BASS-II, Saffire-I/II/III, SAME, SAME-R, DAFT, DAFT-2, FLEX, FLEX-2, CFI, SPICE, SLICE, and the
  six ACME experiments) plus 6 reference habitats.
- Transparent ranking model, coverage-gap analysis, **hybrid search (BM25 + LSA + Reciprocal Rank Fusion)**, and a Gemini
  RAG assistant with a citation guardrail and an offline fallback.
- Evaluation harness (`python -m flame.evaluate`): hybrid MRR 0.98 vs 0.89 for the TF-IDF baseline (25 labelled questions).
- GitHub Actions CI runs the tests and the benchmark on every push.
- **Any-format importer** (`flame/importer.py`): drop CSV/Excel/JSON/PDF/DOCX/TXT/HTML into `data/resources/`.
  Test tables update the condition ranges and mark records verified, and documents become searchable for the AI.
- Docs: `README.md` (overview), `docs/GUIDE.md` (step-by-step use/test, now and after the NASA resources), `notes/CV_NOTES.md`
  (metrics + CV bullets), `docs/HOW_IT_WORKS.md` (code walkthrough).
- 15 tests pass (`python -m pytest`). The Excel, JSON, PDF, DOCX and HTML readers were also checked by hand. The app runs locally with `streamlit run app.py`.
- Ready to deploy on Streamlit Community Cloud (see README).

## Known limitations ⚠️

1. **The data is approximate.** O₂ / pressure / flow ranges and years in `data/investigations.json` come from public
   descriptions, not from PSI files. Every record has `"verified": false`. This is the most important thing to fix.
2. Pillar scores (0–3) and `partial_gravity` are **editorial judgements**. You should be able to justify each one, or change it.
3. The importer only reads condition columns (investigation, fuel, O₂, pressure, flow). Other columns, such as outcome or flame speed, are not used yet.
4. There is no partial-gravity data in PSI yet (LUCI and FM2 are future experiments). The app only shows E-FIELD as a proxy.

## Working without the original chat

**This `notes/` folder is private but currently committed to git** (you chose to include it for now).
Remove it before the repo goes public; see "Removing notes/ before going public" at the end of this file.

- In the public repo: `docs/GUIDE.md` (run, test, add data, publish) and `docs/HOW_IT_WORKS.md` (code).
- Private here: this file (state, TODO, submission checklist) and `CV_NOTES.md` (CV bullets, metrics, interview Q&A).

A fresh `git clone` → `pip install -r requirements.txt` → `python -m pytest` was checked to work on 2026-10-29.

## TODO when the official resources come out

- [ ] Put the resource files into `data/resources/` and click Reload. Open **Data → Imported resources** to see what loaded
      and what was skipped.
- [ ] If a table loaded with 0 test rows, its headers weren't recognised. Add the header words to `ALIASES` in `flame/importer.py`.
- [ ] Records covered by test tables get their ranges recomputed automatically. Check the rest by hand (`year`, `fuels`,
      `measurements`, findings) and set `"verified": true`.
- [ ] After adding data, rerun `python -m flame.evaluate`, add questions for new investigations to `tests/benchmark.json`, and copy
      the new numbers into `notes/CV_NOTES.md`.
- [ ] Optional idea: use Gemini to pull structured fields (fuel, O₂, findings) out of PDF papers. This would go in a new
      function in `importer.py`.
- [ ] Add any new investigations the challenge lists (copy an existing record; `flame/data.py::validate` checks the fields).
- [ ] Optional: if the PSI tables include an outcome column (burned / extinguished), train a simple logistic-regression
      "will it burn?" model on the imported test rows (`resources["tests"]`). This covers the "predictive modelling" objective.
- [ ] Optional: add Saffire-IV/V/VI if they are in PSI. They tested other O₂ / pressure conditions and would fill
      part of the lunar-atmosphere gap.

## Things you can easily tweak

| What | Where |
|---|---|
| Ranking weights / fuel relevance | `flame/ranking.py` (`DEFAULT_WEIGHTS`, `FUEL_RELEVANCE`) |
| Habitat atmospheres | `data/habitats.json` |
| AI model | env var `GEMINI_MODEL` (default `gemini-2.5-flash`) |
| AI prompt | `flame/assistant.py` (`SYSTEM_PROMPT`) |
| Switch AI provider (e.g. Groq) | replace the body of `answer()` in `flame/assistant.py`; nothing else depends on it |

## Interview-defence cheat sheet

- More interview Q&A is in `notes/CV_NOTES.md` section 8.
- **Why BM25 + LSA and not neural embeddings?** About 20 short records: classical IR is fast, offline, reproducible and measurably
  good (0.98 MRR). Neural embeddings would be the upgrade once there are thousands of PSI documents.
- **How does it handle unknown data formats?** Header matching by keywords plus unit conversion, and any file that fails
  is reported, not fatal. Tested with deliberately messy sample files (`;`-separated values, kPa, mole fraction, mm/s).
- **Why RAG?** The LLM only sees retrieved records and must cite IDs, which reduces hallucination. The app still works without a key.
- **Why exp(-distance) for atmosphere fit?** It is 1 inside the tested envelope and decays smoothly outside, with scales of 10 % O₂
  and 4 psi. That expresses "how far are we extrapolating?".
- **Key insight the app shows:** the Moon-base atmosphere (30% O₂, 10.2 psi) is outside every solid-material test in the curated
  dataset (all at ≤21% O₂, ~14.7 psi), even though solids are the main fire load. Only gas-burner and liquid-droplet tests went above
  30% O₂. Re-check against PSI (Saffire-IV–VI) before submitting.

---

## SUBMISSION: NASA Space Apps 2026 checklist

**Always follow the official rules on the Space Apps website.** They are the authority on what to submit and by when. This file
is a checklist and a draft text to adapt.

### Before the deadline

- [ ] **Load the official resources** (docs/GUIDE.md Part B) and check the data. Remove or clearly label anything still approximate.
- [ ] Rerun `python -m pytest` and `python -m flame.evaluate`, and update the numbers in `README.md` and `notes/CV_NOTES.md` if they changed.
- [ ] **Deploy** (docs/GUIDE.md Part C) and test the live link in a private browser window.
- [ ] Test the **Ask** tab with your Gemini key on the live app (docs/GUIDE.md A4).
- [ ] Record a **short demo video**. Check the official length limit. Suggested script below.
- [ ] Make a few **slides** if required: problem, solution, demo screenshots, key insight, tech, next steps.
- [ ] Fill in the **project page**: title, description (draft below), links to the live app, GitHub repo and video.
- [ ] Declare **AI tool usage** if the rules ask for it. Gemini is used inside the app, and AI assistance was used while developing it.
- [ ] Credit **NASA data**: list the PSI datasets and resources you used, by name and link.
- [ ] Make sure the GitHub repo is **public** and the README badge is green.

### Draft project description (adapt it)

> **Flame in Freefall** helps engineers and researchers turn decades of NASA microgravity combustion experiments into fire-safety
> answers for the Moon, Mars and beyond.
>
> Choose a crew habitat, such as the ISS, a pressurized lunar rover at 30% O₂ / 10.2 psi, or a Mars base. Then pick what matters
> most: preventing, detecting or suppressing fire. The dashboard **ranks** every investigation (BASS, Saffire, FLEX, ACME, SAME…)
> with a transparent score, **maps** the oxygen and pressure each experiment actually tested against crew atmospheres, and lets
> you **compare** investigations side by side. An **AI assistant** answers plain-English questions using only NASA records, with
> cited sources and a guardrail against made-up citations.
>
> **Key finding:** the planned Moon-base atmosphere lies outside every solid-material test in our curated dataset, even though fabrics and
> plastics are the main fire load in a cabin. That points to where the next experiments (such as FM2 and LUCI) matter most.
>
> The app ingests NASA resources in any common format (CSV, Excel, JSON, PDF, Word, HTML), so new PSI data can be dropped in
> without code changes.
>
> **Tech:** Python, Streamlit, scikit-learn (BM25 + LSA hybrid retrieval with Reciprocal Rank Fusion), Google Gemini (RAG), Plotly.

### Demo video script (~60–90 s)

1. **(10 s) Problem:** "NASA has decades of fire experiments from the ISS, but they're hard to find and compare, and the Moon base will
   have 40% more oxygen than Earth."
2. **(20 s) Rank tab:** pick *Moon Base*, move the priority sliders, and show the ranking change.
3. **(20 s) Atmosphere gaps:** show the stars outside the solid-material boxes and the warning. State the key finding.
4. **(15 s) Compare:** show two investigations side by side.
5. **(15 s) Ask:** type a question and show the cited answer.
6. **(5 s) Close:** "Drop in new NASA data in any format, and it updates automatically."


---

## Removing notes/ before going public

`git rm` alone is **not enough**: the files would still be visible in old commits on GitHub. Do this instead.

**Step 1: back up the folder** (copy `notes/` to Google Drive or another folder outside the project).

**Step 2: rebuild the history without notes/** (run in the project root; it keeps all your current code):

```bash
echo notes/>> .gitignore
git rm -r -q --cached notes
git checkout --orphan clean
git add -A
git commit -m "Flame in Freefall: AI fire-safety dashboard for NASA microgravity combustion data"
git branch -D main
git branch -m main
git reflog expire --expire=now --all
git gc --prune=now
```

**Step 3: check it worked.** This should print nothing:

```bash
git log --all --name-only --format="" | findstr notes
```

The `notes/` folder stays on your PC (it's only removed from git).

**Step 4: push.**
- Never pushed before: `git push -u origin main`.
- Already pushed to GitHub with notes in it: `git push --force -u origin main`. Treat what was public as already seen,
  because GitHub or others may have cached it. If that happened, the simplest clean option is to delete the GitHub repo and
  create a new one before pushing.
