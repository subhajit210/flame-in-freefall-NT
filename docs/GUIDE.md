# Guide: run, test, add NASA data, deploy

- **Part A**: set up, use and test it **now** (no NASA files needed).
- **Part B**: add the **official challenge resources** (any format).
- **Part C**: publish (GitHub + free hosting).
- **Part D**: troubleshooting.

Commands are for Windows. On macOS/Linux use `source .venv/bin/activate` instead of `.venv\Scripts\activate`.
Always run commands from the project root folder.

---

## Part A: use and test it now

### A1. One-time setup (≈3 min)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

✅ The install finishes without errors, and `(.venv)` appears at the start of your prompt.

### A2. Run the tests and the benchmark

```bash
python -m pytest
python -m flame.evaluate
```

✅ `15 passed`. The benchmark table shows **Hybrid BM25 + LSA (RRF)** with the best MRR (≈0.98) and `100% of 40` header variants.

### A3. Start the app and click through

```bash
streamlit run app.py
```

Open **http://localhost:8501**:

| # | Do this | You should see |
|---|---|---|
| 1 | Look at the sidebar | Habitat = *Moon Base / pressurized rover*, three priority sliders, "AI assistant: offline mode" |
| 2 | **🎯 Rank** tab | A table sorted by score with bars. Top 3: ACME-BRE, FLEX, BASS |
| 3 | Sidebar: Detection = 3, Prevention = 0, Suppression = 0 | SAME / SAME-R jump to the top (smoke detection studies) |
| 4 | Change habitat to *ISS / Orion cabin* | The **atmosphere** column becomes 1.0 for every row |
| 5 | **🗺️ Atmosphere gaps** tab, habitat *Moon Base* | Coloured boxes (test ranges), black stars (crew atmospheres), and a yellow warning that no solid-material test covers it |
| 6 | **⚖️ Compare** tab | Side-by-side table for BASS-II / Saffire-I / FLEX and a radar chart |
| 7 | **🤖 Ask**: *"How was smoke detection studied in microgravity?"* | An answer listing SAME / SAME-R. The caption says "Retrieved by hybrid search…" |
| 8 | **📄 Data** tab | Full table, **Download CSV**, an "Imported resources" panel (empty for now), details box |

### A4. (Optional) Turn on real AI answers: the Gemini API key

The only key this project uses is a **Google Gemini API key**. It's free and needs no credit card. Without it, everything still
works, and the 🤖 Ask tab gives an offline answer (a list of the matching investigations) instead of a written one.

**Step 1: get the key**
1. Go to https://aistudio.google.com/apikey and sign in with any Google account.
2. Click **Create API key**. If it asks for a project, choose any or create one.
3. Copy the key. It's a long string starting with `AIza…`.

**Step 2: paste it where the app can read it (on your PC)**

Create the file **`.streamlit/secrets.toml`** inside the project folder, next to `app.py`. Run these from the project root:

```bash
mkdir .streamlit
notepad .streamlit\secrets.toml
```

Notepad asks to create the file; click **Yes**. Paste this one line with your key inside the quotes, then save:

```toml
GEMINI_API_KEY = "AIza...your-key..."
```

The result should look like this:

```
nasa_space_challange/
├── app.py
└── .streamlit/
    └── secrets.toml      ← contains GEMINI_API_KEY = "..."
```

**Step 3: check it works**
1. Restart the app: press `Ctrl+C` in the terminal, then run `streamlit run app.py` again.
2. The sidebar should say **"AI assistant: Gemini ✅"** instead of "offline mode".
3. In 🤖 Ask, type a question. You get a written answer with `[IDs]`. If Gemini ever cites something it wasn't given, a
   ⚠️ *Citation check* line appears under the answer.

**Where the key goes in each situation**

| Where the app runs | Where to paste the key |
|---|---|
| Your PC | `.streamlit/secrets.toml`, as above |
| Streamlit Cloud (the live link) | App → **⋮ → Settings → Secrets** (or *Advanced settings → Secrets* while deploying). Paste the same `GEMINI_API_KEY = "..."` line and save. The app restarts on its own |
| Terminal only (alternative) | PowerShell: `$env:GEMINI_API_KEY="AIza..."`, then `streamlit run app.py` in the same window |

**Optional second setting:** if Google retires the default model (`gemini-2.5-flash`), add a second line with a current model
name from https://ai.google.dev/gemini-api/docs/models:

```toml
GEMINI_MODEL = "gemini-x.x-flash"
```

**Keep the key safe**
- `.streamlit/secrets.toml` is in `.gitignore`, so git never uploads it. **Never** paste the key into `app.py` or any other code file,
  the README, or a commit.
- If a key leaks (for example, it gets pushed to GitHub), delete it in AI Studio and create a new one.
- The free tier has rate limits. If you hit one, you'll see *"AI call failed"* and the offline answer, and it works again after a minute.

### A5. Try the "any format" importer

1. Create `data/resources/sample.csv` with this content (semicolons, a fraction, kPa and mm/s are deliberate):

   ```
   Experiment;Sample material;Oxygen mole fraction;Pressure [kPa];Flow velocity (mm/s)
   BASS-II;PMMA;0.17;101.3;50
   BASS-II;PMMA;0.19;101.3;120
   New Rover Test;Nomex;0.30;70.3;100
   ```

2. Click **🔄 Reload data/resources** in the sidebar.
3. Check:
   - **📄 Data → Imported resources**: 3 rows with O₂ 17–30 %, pressure ≈14.7 / 10.2 psi, flow 5–12 cm/s
   - **🎯 Rank**: a new *New Rover Test* row appears, and BASS-II now has O₂ 17–19
4. **Delete `sample.csv` afterwards.** It's fake data.

---

## Part B: add the official challenge resources

### B1. Collect

- Download tables (CSV / Excel / JSON) and documents (PDF / DOCX) from the challenge's **Resources** tab and NASA PSI.
- Web pages: save them as **HTML** (Ctrl+S) or paste the text into a `.txt` file.
- Files over ~50 MB: keep only the useful columns or rows and save a smaller CSV (GitHub and Streamlit have size limits).

### B2. Load

Put everything in **`data/resources/`** (subfolders are fine) and click **🔄 Reload data/resources**.

| You drop… | What happens |
|---|---|
| **Tables** (`.csv .tsv .xlsx .xls .json`) with test conditions | Each row counts as one test. Each investigation's O₂ / pressure / flow ranges are **recomputed from the rows** and it's marked `verified`. Unknown investigation names become new records |
| **Tables without those columns** | Become searchable text for the Ask tab |
| **Documents** (`.pdf .docx .txt .md .html`) | Text is split into ~1500-character passages. Ask searches and cites them |
| **Anything else** (images, zip…) | Listed as *skipped*. Nothing breaks |

How headers are recognised (`ALIASES` and `UNITS` in `flame/importer.py`; case and punctuation are ignored):

| Column | Header words | Units converted |
|---|---|---|
| investigation | investigation, experiment, payload, project, study | (file name if missing) |
| fuel | fuel, material, sample | |
| O₂ | o2, oxygen, xo2 | % or 0–1 fraction |
| pressure | pressure, press | psi (default), kPa, MPa, bar, atm |
| flow | flow, velocity, speed | cm/s (default), mm/s, m/s |

### B3. Check what loaded (📄 Data → Imported resources)

| You see | Meaning | Do this |
|---|---|---|
| Rows in the test table | ✅ Recognised | Sanity-check the numbers (O₂ 0–100 %, psi, cm/s) |
| A table **missing** from the test table | Headers not recognised | Add the header's key word to `ALIASES` (one line), then Reload |
| ⚠️ *Skipped …* | Unsupported format or scanned PDF | Convert it to CSV/TXT, or ignore it |
| Duplicates like "BASS 2" vs "BASS-II" | Name differs from our id | Rename the value in the file to the id in `data/investigations.json` |

Then, for records the files didn't cover, edit `data/investigations.json` by hand (year, fuels, findings) and set
`"verified": true`. Add new investigations by copying an existing block.

### B4. Re-test and re-measure

```bash
python -m pytest
python -m flame.evaluate
```

If you added investigations, add 1–2 questions for them to `tests/benchmark.json`, writing the expected ids **before** you look
at the results. Rerun, and update the numbers in `README.md`.

### B5. Ship

```bash
git add -A
git commit -m "Add official NASA resources"
git push
```

Streamlit Cloud redeploys automatically and GitHub Actions reruns the tests.

---

## Part C: publish for the first time

**GitHub:**
1. Create a **public** repo at https://github.com/new (no README).
2. Run:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

3. In `README.md` line 3, replace `<your-username>/flame-in-freefall` with your username and repo name, then commit and push.
4. The repo's **Actions** tab should turn green.

**Streamlit Community Cloud (free):**
1. Go to https://share.streamlit.io, sign in with GitHub, and click **Create app** → pick the repo, branch `main`, file `app.py`.
2. **Advanced settings → Secrets:** `GEMINI_API_KEY = "your-key"`.
3. Click **Deploy**. You get a `*.streamlit.app` URL in 2–3 minutes. Run the A3 checklist on it.

---

## Part D: troubleshooting

| Problem | Fix |
|---|---|
| `streamlit: command not found` | Activate the venv, or run `python -m streamlit run app.py` |
| `ModuleNotFoundError: flame` | Run from the project root, and use `python -m pytest` (not bare `pytest`) |
| Offline mode although a key is set | The file must be exactly `.streamlit/secrets.toml`, next to `app.py`. Windows may have saved it as `secrets.toml.txt`: check with `dir .streamlit` and rename it. Then restart the app |
| *"AI call failed (ClientError)"* right after adding the key | The key is wrong or has extra spaces. Copy it again from AI Studio, keeping the quotes: `GEMINI_API_KEY = "AIza..."` |
| *"AI call failed (…)"* | Quota or bad key. The offline answer is still shown. Retry later or check the key |
| AI fails with a model error / 404 | Google retired the model. Pick a current Flash model at https://ai.google.dev/gemini-api/docs/models and add `GEMINI_MODEL = "name"` to the secrets |
| Changes in `data/` not showing | Click **🔄 Reload data/resources** (data is cached) |
| `pip install` fails | Use Python 3.11–3.13 |
| A test fails after editing the JSON | The error names the record id and the bad field |
| Benchmark test fails after adding data | Rankings changed. Rerun `python -m flame.evaluate`, and only relax the threshold in `tests/test_core.py` if the drop is real and explained |
