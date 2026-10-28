# User Guide

This guide covers installation, verification, adding NASA data, deployment and troubleshooting.

1. Setup and verification
2. Configuring the Gemini API key
3. Adding NASA resources
4. Deployment
5. Troubleshooting

Commands assume Windows and must be run from the project root. On macOS or Linux, activate the environment with
`source .venv/bin/activate`.

## 1. Setup and verification

### 1.1 Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.11 to 3.13 is required. After activation, the prompt is prefixed with `(.venv)`.

### 1.2 Tests and benchmark

```bash
python -m pytest
python -m flame.evaluate
```

Expected results: `15 passed`. The benchmark reports an MRR of approximately 0.98 for the fused BM25 + LSA method and maps
40 of 40 header variants correctly.

### 1.3 Running the application

```bash
streamlit run app.py
```

The application opens at http://localhost:8501. The checks below confirm that each view works.

| Step | Action | Expected result |
|---|---|---|
| 1 | Inspect the sidebar | Habitat set to "Moon Base / pressurized rover"; three priority sliders; assistant status "offline mode" |
| 2 | Open the Rank view | Investigations sorted by score; the top three are ACME-BRE, FLEX and BASS |
| 3 | Set Detection to 3, Prevention and Suppression to 0 | SAME and SAME-R move to the top |
| 4 | Select the "ISS / Orion cabin" habitat | The atmosphere column is 1.0 for all investigations |
| 5 | Open Atmosphere gaps with the Moon Base habitat | Test envelopes, crew atmospheres, and a warning that no solid-material test covers the habitat |
| 6 | Open Compare | Comparison table and radar chart for BASS-II, Saffire-I and FLEX |
| 7 | In Ask, enter "How was smoke detection studied in microgravity?" | An answer that includes SAME and SAME-R, with the retrieved sources listed below it |
| 8 | Open Data | Investigation table, CSV download, an empty "Imported resources" panel, and a details panel |

### 1.4 Testing the importer

1. Create `data/resources/sample.csv` with the content below. The semicolon delimiter, oxygen fraction, kPa and mm/s are
   intentional.

   ```
   Experiment;Sample material;Oxygen mole fraction;Pressure [kPa];Flow velocity (mm/s)
   BASS-II;PMMA;0.17;101.3;50
   BASS-II;PMMA;0.19;101.3;120
   New Rover Test;Nomex;0.30;70.3;100
   ```

2. Click "Reload data/resources" in the sidebar.
3. Verify the result:
   - **Data view → Imported resources:** three rows with oxygen 17–30%, pressure 14.7 and 10.2 psi, and flow 5–12 cm/s.
   - **Rank view:** a new "New Rover Test" entry, and BASS-II with an oxygen range of 17–19%.
4. Delete `sample.csv`. It is test data only.

## 2. Configuring the Gemini API key

The project uses a single external service, the Google Gemini API, to generate answers in the Ask view. A key is free and does not
require a payment method. Without a key, the Ask view returns an extractive summary of the retrieved investigations, and all other
features work normally.

### 2.1 Obtaining a key

1. Go to https://aistudio.google.com/apikey and sign in with a Google account.
2. Select "Create API key" and choose or create a project if prompted.
3. Copy the key. It begins with `AIza`.

### 2.2 Local configuration

Create `.streamlit/secrets.toml` in the project root:

```bash
mkdir .streamlit
notepad .streamlit\secrets.toml
```

Add the following line, with your key between the quotation marks, and save the file:

```toml
GEMINI_API_KEY = "AIza..."
```

The file must be located at `.streamlit/secrets.toml`, alongside `app.py`.

### 2.3 Verification

Restart the application (stop it with Ctrl+C, then run `streamlit run app.py` again). The sidebar status changes from "offline mode"
to "Gemini (online)". Questions in the Ask view now return generated answers with bracketed investigation identifiers. If an answer cites an
identifier that was not retrieved, a citation warning is shown beneath it.

### 2.4 Key location by environment

| Environment | Location |
|---|---|
| Local machine | `.streamlit/secrets.toml` |
| Streamlit Community Cloud | App settings → Secrets (or Advanced settings → Secrets during deployment), with the same line |
| Single terminal session | `$env:GEMINI_API_KEY="AIza..."` in PowerShell, then start the app in the same window |

### 2.5 Model selection

The default model is `gemini-2.5-flash`. If it is retired, add a current model name, as listed at
https://ai.google.dev/gemini-api/docs/models, to the same secrets file:

```toml
GEMINI_MODEL = "model-name"
```

### 2.6 Security

- `.streamlit/secrets.toml` is excluded by `.gitignore`. Do not place the key in source files, documentation or commits.
- If a key is exposed, revoke it in Google AI Studio and create a new one.
- The free tier is rate-limited. When a limit is reached, the application shows the extractive answer until requests are accepted again.

## 3. Adding NASA resources

### 3.1 Collecting files

- Download tables (CSV, Excel, JSON) and documents (PDF, DOCX) from the challenge Resources page and NASA PSI.
- Save web pages as HTML, or copy their text into a `.txt` file.
- For files larger than about 50 MB, keep only the required rows or columns. GitHub and Streamlit Community Cloud impose size limits.

### 3.2 Loading

Place the files in `data/resources/` (subfolders are supported) and click "Reload data/resources".

| Input | Handling |
|---|---|
| Tables with test conditions (`.csv`, `.tsv`, `.xlsx`, `.xls`, `.json`) | Each row is treated as a test. Investigation condition ranges are recomputed from the rows, and the record is marked verified. Unrecognised investigations are added as new records. |
| Tables without condition columns | Indexed as text for the Ask view |
| Documents (`.pdf`, `.docx`, `.txt`, `.md`, `.html`) | Split into passages of about 1,500 characters and indexed for the Ask view |
| Other formats | Listed as skipped |

Column recognition is defined by `ALIASES` and `UNITS` in `flame/importer.py`. Matching ignores case and punctuation.

| Column | Header keywords | Unit handling |
|---|---|---|
| investigation | investigation, experiment, payload, project, study | File name is used if absent |
| fuel | fuel, material, sample | — |
| oxygen | o2, oxygen, xo2 | Percent or mole fraction |
| pressure | pressure, press | psi (default), kPa, MPa, bar, atm |
| flow | flow, velocity, speed | cm/s (default), mm/s, m/s |

### 3.3 Reviewing the import

Open **Data → Imported resources**.

| Observation | Cause | Action |
|---|---|---|
| Rows appear in the test table | File recognised | Check that values are plausible (oxygen 0–100%, pressure in psi, flow in cm/s) |
| A table is absent from the test table | Headers not recognised | Add the header keyword to `ALIASES`, then reload |
| File listed as skipped | Unsupported format or image-only PDF | Convert it to CSV or text, or omit it |
| Duplicate investigations (e.g. "BASS 2" and "BASS-II") | Name differs from the existing identifier | Use the identifier from `data/investigations.json` in the source file |

For investigations not covered by imported data, update `data/investigations.json` manually and set `"verified": true`. New
investigations can be added by copying an existing record.

### 3.4 Re-running tests and evaluation

```bash
python -m pytest
python -m flame.evaluate
```

When adding investigations, also add one or two questions for them to `tests/benchmark.json`. Record the expected identifiers
before running the evaluation, then update the results table in `README.md`.

### 3.5 Publishing changes

```bash
git add -A
git commit -m "Add NASA resources"
git push
```

Streamlit Community Cloud redeploys automatically after each push, and GitHub Actions runs the test suite.

## 4. Deployment

### 4.1 GitHub

1. Create a repository at https://github.com/new without initialising a README.
2. Add the remote and push:

   ```bash
   git remote add origin https://github.com/<username>/<repository>.git
   git push -u origin main
   ```

3. In `README.md`, replace `<your-username>/flame-in-freefall` in the badge URL with your username and repository name, then commit and push.
4. Confirm that the workflow in the Actions tab passes.

### 4.2 Streamlit Community Cloud

1. Sign in at https://share.streamlit.io with GitHub and create an app from the repository (branch `main`, file `app.py`).
2. Under Advanced settings → Secrets, add `GEMINI_API_KEY = "..."`.
3. Deploy. The application is available at a `*.streamlit.app` address within a few minutes. Repeat the checks in section 1.3 on the deployed version.

## 5. Troubleshooting

| Problem | Resolution |
|---|---|
| `streamlit: command not found` | Activate the virtual environment, or run `python -m streamlit run app.py` |
| `ModuleNotFoundError: flame` | Run commands from the project root and use `python -m pytest` |
| Assistant remains in offline mode | Confirm the file is named exactly `.streamlit/secrets.toml` (Windows may save it as `secrets.toml.txt`; check with `dir .streamlit`), then restart the application |
| "AI call failed (ClientError)" after adding a key | The key is invalid or contains extra characters. Copy it again and keep the quotation marks |
| "AI call failed" during use | Rate limit or network error. The extractive answer is shown; retry later |
| Model error or HTTP 404 | The model has been retired. Set `GEMINI_MODEL` as described in section 2.5 |
| Changes in `data/` are not reflected | Click "Reload data/resources"; data is cached |
| `pip install` fails | Use Python 3.11 to 3.13 |
| A test fails after editing the dataset | The error message identifies the record and field |
| The benchmark test fails after adding data | Rankings have changed. Re-run `python -m flame.evaluate` and review the results. Relax the threshold in `tests/test_core.py` only if the change is understood |
