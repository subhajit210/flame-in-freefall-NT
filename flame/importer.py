"""Import whatever resource files are dropped into data/resources/.

* Tables    (.csv .tsv .xlsx .xls .json) -> per-test rows with O2 / pressure / flow, grouped by investigation.
* Documents (.pdf .docx .txt .md .html)  -> plain-text passages that search and the AI assistant can use.

Column names are matched loosely ("O2 (%)", "Oxygen mole fraction", "Pressure [kPa]") and units are converted
to %, psi and cm/s. Files that cannot be read are reported as skipped instead of crashing the app.
"""
import json
import re
import zipfile
from pathlib import Path

import pandas as pd

TABLE_EXT = {".csv", ".tsv", ".xlsx", ".xls", ".json"}
DOC_EXT = {".pdf", ".docx", ".txt", ".md", ".html", ".htm"}
RANGES = ("o2_pct", "pressure_psi", "flow_cm_s")
CHUNK_CHARS = 1500

# Standard column -> words that identify it in a messy header, strongest keyword first.
# "o" is a deliberate last resort for element-composition headers such as "O ... mole fraction" (PSI FLEX).
ALIASES = {
    "investigation": ["investigation", "experiment", "payload", "project", "study"],
    "fuel": ["fuel", "material", "sample"],
    "o2_pct": ["o2", "oxygen", "xo2", "o"],
    "pressure_psi": ["pressure", "press"],
    "flow_cm_s": ["flow", "velocity", "speed"],
    "objective": ["objective", "description", "summary"],
}
# Unit found in the header -> factor to psi / cm/s. Order matters: "cm/s" must be tested before "m/s".
UNITS = {
    "pressure_psi": [("kpa", 1 / 6.895), ("mpa", 145.04), ("bar", 14.504), ("atm", 14.696),
                     ("mmhg", 0.0193368), ("torr", 0.0193368)],
    "flow_cm_s": [("mm/s", 0.1), ("cm/s", 1.0), ("m/s", 100.0)],
}


_NUMBER = re.compile(r"[-+]?\d*\.?\d+")


def _norm(text) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _cell_number(value) -> float:
    """Pull a number out of a messy cell: '21.5 - 21.7' -> 21.6, '~ 21.5' -> 21.5, '<10' -> 10.

    Real PSI tables record conditions as text ranges or approximations, so the mean of the numbers
    found in the cell is used as that test's representative value.
    """
    nums = _NUMBER.findall(str(value))
    return sum(float(n) for n in nums) / len(nums) if nums else float("nan")


def match_columns(columns) -> dict:
    """Map our standard names to the actual column names found in a table.

    Each alias list is ordered strongest keyword first, so a 'Material' column wins the fuel slot over a
    'Sample Number' column (both contain a keyword, but 'material' outranks the weaker 'sample').
    """
    words = {c: set(_norm(c).split()) for c in columns}
    found = {}
    for std, keywords in ALIASES.items():
        for kw in keywords:
            col = next((c for c in columns if c not in found.values() and kw in words[c]), None)
            if col is not None:
                found[std] = col
                break
    return found


def unit_factor(std: str, header: str) -> float:
    tokens, compact = _norm(header).split(), str(header).lower().replace(" ", "")
    for unit, factor in UNITS.get(std, []):
        if (unit in compact) if "/" in unit else (unit in tokens):
            return factor
    return 1.0  # already psi / cm/s


def normalize_table(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Standard columns: investigation, fuel, o2_pct, pressure_psi, flow_cm_s, objective, source."""
    cols = match_columns(df.columns)
    out = pd.DataFrame(index=df.index)
    out["investigation"] = df[cols["investigation"]].astype(str) if "investigation" in cols else Path(source).stem
    out["fuel"] = df[cols["fuel"]].astype(str) if "fuel" in cols else ""
    for std in RANGES:
        out[std] = df[cols[std]].map(_cell_number) * unit_factor(std, cols[std]) if std in cols else float("nan")
    # Physical sanity: O2 and pressure must be positive, so 0 means "not recorded" (flow of 0 is valid).
    for std in ("o2_pct", "pressure_psi"):
        out.loc[out[std] <= 0, std] = float("nan")
    if out["o2_pct"].max() <= 1.0:  # given as a mole fraction
        out["o2_pct"] *= 100
    out["objective"] = df[cols["objective"]].astype(str) if "objective" in cols else ""
    out["source"] = Path(source).name
    return out.dropna(subset=list(RANGES), how="all")


def _read_table(path: Path) -> pd.DataFrame:
    ext = path.suffix.lower()
    if ext in (".csv", ".tsv"):
        sep = None if ext == ".csv" else "\t"  # None sniffs , ; tab
        # NASA exports vary: utf-8-sig strips a BOM; cp1252/latin-1 handle Windows en-dashes etc.
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return pd.read_csv(path, sep=sep, engine="python", encoding=enc)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path, sep=sep, engine="python", encoding="latin-1")  # never raises
    if ext in (".xlsx", ".xls"):
        return pd.concat(pd.read_excel(path, sheet_name=None).values(), ignore_index=True)  # all sheets
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):  # {"tests": [...]} or similar - take the first list
        data = next((v for v in data.values() if isinstance(v, list)), [data])
    return pd.json_normalize(data)


def _read_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    if ext == ".docx":  # a .docx is a zip; the text lives in word/document.xml
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
        return re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n"))
    text = path.read_text(encoding="utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        text = re.sub(r"<(script|style).*?</\1>|<[^>]+>", " ", text, flags=re.S | re.I)
    return text


def chunk(text: str, title: str) -> list[dict]:
    """Split text into ~CHUNK_CHARS passages on line boundaries, so search can point to the right part."""
    chunks, current = [], ""
    for line in (l.strip() for l in re.sub(r"[ \t]+", " ", text).splitlines()):
        if current and len(current) + len(line) > CHUNK_CHARS:
            chunks.append(current)
            current = ""
        if line:
            current += line + "\n"
    chunks += [current] if current else []
    return [{"title": title, "part": i + 1, "text": c.strip()} for i, c in enumerate(chunks)]


def load_resources(folder: Path) -> dict:
    """Read every file in `folder`. Returns {"tests": DataFrame, "documents": [passages], "skipped": [(file, reason)]}."""
    tests, docs, skipped = [], [], []
    for path in sorted(p for p in Path(folder).rglob("*") if p.is_file() and not p.name.startswith(".")):
        ext = path.suffix.lower()
        try:
            if ext in TABLE_EXT:
                raw = _read_table(path)
                table = normalize_table(raw, path.name)
                if table.empty:  # no O2/pressure/flow columns: still useful as searchable text
                    docs += chunk(raw.to_csv(index=False), path.name)
                else:
                    tests.append(table)
            elif ext in DOC_EXT:
                text = _read_text(path)
                if text.strip():
                    docs += chunk(text, path.name)
                else:
                    skipped.append((path.name, "no extractable text (scanned PDF?)"))
            else:
                skipped.append((path.name, f"unsupported format {ext or '(none)'}"))
        except Exception as e:  # never let one bad file break the dashboard
            skipped.append((path.name, f"{type(e).__name__}: {e}"))
    columns = ["investigation", "fuel", *RANGES, "objective", "source"]
    return {"tests": pd.concat(tests, ignore_index=True) if tests else pd.DataFrame(columns=columns),
            "documents": docs, "skipped": skipped}


ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8"}


def _fold(text) -> str:
    """Normalise an investigation name for matching: lowercase, drop punctuation, fold roman numerals.

    So 'SAFFIRE-1' (PSI) and 'Saffire-I' (dataset) both become 'saffire1'.
    """
    return "".join(ROMAN.get(t, t) for t in re.findall(r"[a-z]+|\d+", str(text).lower()))


def _match_record(inv: str, lookup: dict) -> dict | None:
    """Find the dataset record an imported investigation belongs to, by exact fold or by the longest
    known id/name embedded in it (handles 'PSI-98_Experimental table_SAFFIRE-1' -> Saffire-I)."""
    folded = _fold(inv)
    if folded in lookup:
        return lookup[folded]
    hits = [(k, v) for k, v in lookup.items() if len(k) >= 4 and k in folded]
    return max(hits, key=lambda kv: len(kv[0]))[1] if hits else None


def merge_tests(records: list[dict], tests: pd.DataFrame) -> list[dict]:
    """Update records with condition ranges measured from imported test rows.

    Rows whose investigation matches an existing id/name (ignoring case, punctuation and roman/arabic
    numerals, including a name embedded in the file name) update that record and mark it verified.
    Unknown investigations become new, minimal records so they still appear in every tab.
    """
    lookup = {_fold(r[f]): r for r in records for f in ("id", "name")}
    merged = {r["id"]: r for r in records}
    for inv, group in tests.groupby("investigation"):
        known = [v for v in group["objective"] if v and v != "nan"]
        rec = _match_record(inv, lookup) or {
            "id": str(inv), "name": str(inv), "family": "Imported", "hardware": "unknown", "year": 0,
            "fuel_phase": "unknown", "fuels": sorted({f for f in group["fuel"] if f and f != "nan"}),
            "objective": known[0] if known else f"Imported from {', '.join(group['source'].unique())}.",
            "conditions": {k: [0, 0] for k in RANGES} | {"diluents": []},
            "measurements": [], "key_findings": [],
            "safety_pillars": {"prevention": 1, "detection": 1, "suppression": 1},
        }
        rec = {**rec, "conditions": dict(rec["conditions"]), "verified": True, "n_tests": len(group)}
        for col in RANGES:
            vals = group[col].dropna()
            if not vals.empty:
                rec["conditions"][col] = [round(float(vals.min()), 2), round(float(vals.max()), 2)]
        merged[rec["id"]] = rec
    return list(merged.values())


if __name__ == "__main__":
    # Quick terminal preview of what data/resources/ would load, without starting Streamlit.
    #   python -m flame.importer
    from flame.data import RESOURCES_DIR, load_investigations

    res = load_resources(RESOURCES_DIR)
    tests, docs, skipped = res["tests"], res["documents"], res["skipped"]
    print(f"Scanning {RESOURCES_DIR}\n")
    print(f"Test rows:      {len(tests)}")
    print(f"Investigations: {tests['investigation'].nunique() if not tests.empty else 0}"
          f" {sorted(tests['investigation'].unique()) if not tests.empty else ''}")
    print(f"Documents:      {len(docs)} passages from {len({d['title'] for d in docs})} file(s)")
    print(f"Skipped:        {len(skipped)}")
    for name, reason in skipped:
        print(f"  - {name}: {reason}")
    if not tests.empty:
        seed = load_investigations()
        lookup = {_fold(r[f]): r for r in seed for f in ("id", "name")}
        mapped = {str(i): (_match_record(i, lookup) or {}).get("id") for i in tests["investigation"].unique()}
        for src, dest in mapped.items():
            print(f"  {src!r} -> {dest if dest else 'NEW record'}")
        print("\nTest table preview:")
        print(tests.to_string(index=False, max_rows=20))
