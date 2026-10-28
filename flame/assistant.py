"""AI assistant: retrieval-augmented answers over the investigation dataset.

1. Retrieve the most relevant investigations (and document passages) with hybrid search (flame/search.py).
2. If GEMINI_API_KEY is set, ask Gemini to answer using ONLY that retrieved context.
3. Citation guardrail: every [citation] in the answer must refer to a retrieved source; others are flagged.
4. Without a key (or on any API error) return an offline, template-based summary of the retrieved items.
"""
import json
import os
import re

DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are a spacecraft fire-safety research assistant. Answer using ONLY the NASA "
    "microgravity combustion investigation records and document passages provided. Cite "
    "investigation IDs or document titles in square brackets, e.g. [BASS-II]. Be concise "
    "(under 200 words), use bullet points, and say clearly when the context does not cover "
    "something (for example partial gravity or oxygen levels outside the tested ranges). "
    "Records with verified=false have approximate condition values."
)


def _compact(record: dict) -> dict:
    keep = ["id", "name", "hardware", "fuel_phase", "fuels", "objective", "conditions",
            "variables", "measurements", "key_findings", "earth_applications", "verified"]
    return {k: record[k] for k in keep if k in record}


def offline_answer(question: str, hits: list[tuple[dict, float]], doc_hits: list[tuple[dict, float]] = ()) -> str:
    if not hits and not doc_hits:
        return "No matching investigations found. Try other keywords (e.g. 'oxygen', 'smoke', 'extinguish')."
    lines = [f"**Most relevant investigations for:** _{question}_\n"]
    for r, sim in hits:
        c = r["conditions"]
        finding = r["key_findings"][0] if r["key_findings"] else r["objective"]
        lines.append(
            f"- **[{r['id']}] {r['name']}** —{r['objective']}  \n"
            f"  O2 {c['o2_pct'][0]}–{c['o2_pct'][1]}%, {c['pressure_psi'][0]}–{c['pressure_psi'][1]} psi. "
            f"Key finding: {finding}"
        )
    for d, sim in doc_hits:
        lines.append(f"- Document **[{d['title']} p{d['part']}]** —{d['text'][:300]}…")
    lines.append("\n_Offline mode: add a GEMINI_API_KEY for AI-written answers._")
    return "\n".join(lines)


def check_citations(text: str, hits, doc_hits=()) -> list[str]:
    """Return citations in `text` that do not match any retrieved source (possible hallucinations)."""
    allowed = {r["id"].lower() for r, _ in hits}
    allowed |= {d["title"].lower() for d, _ in doc_hits}
    allowed |= {f"{d['title']} p{d['part']}".lower() for d, _ in doc_hits}
    bad = []
    for cited in re.findall(r"\[([^\[\]]+)\]", text):
        parts = [p.strip().lower() for p in cited.split(",")]  # handles "[BASS, BASS-II]"
        bad += [p for p in parts if p and p not in allowed]
    return bad


def ai_available() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def answer(question: str, hits: list[tuple[dict, float]], doc_hits: list[tuple[dict, float]] = ()) -> str:
    """Answer a question from retrieved context; falls back to offline mode on any API problem."""
    if not ai_available() or not (hits or doc_hits):
        return offline_answer(question, hits, doc_hits)
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        context = json.dumps({
            "records": [_compact(r) for r, _ in hits],
            "documents": [{"title": d["title"], "part": d["part"], "text": d["text"]} for d, _ in doc_hits],
        }, indent=1)
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", DEFAULT_MODEL),
            contents=f"Context:\n{context}\n\nQuestion: {question}",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.2),
        )
        text = response.text or ""
        if not text:
            return offline_answer(question, hits, doc_hits)
        unsupported = check_citations(text, hits, doc_hits)
        if unsupported:
            text += f"\n\n_Citation check: {', '.join(sorted(set(unsupported)))} not in retrieved sources - verify._"
        return text
    except Exception as e:  # network, quota, bad key... keep the app usable
        return offline_answer(question, hits, doc_hits) + f"\n\n_AI call failed ({type(e).__name__}); showing offline answer._"
