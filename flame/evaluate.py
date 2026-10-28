"""Measure retrieval quality and column-mapping accuracy on the labelled benchmark (tests/benchmark.json).

Run:  python -m flame.evaluate

Hit@k : share of questions where at least one correct investigation is in the top k results.
MRR   : Mean Reciprocal Rank = average of 1 / (rank of the first correct result). 1.0 = always first.
"""
import json
import time
from pathlib import Path

from flame.data import load_investigations
from flame.importer import match_columns
from flame.search import SearchIndex

BENCHMARK = Path(__file__).resolve().parent.parent / "tests" / "benchmark.json"
METHODS = {"tfidf": "TF-IDF (baseline)", "bm25": "BM25", "lsa": "LSA (TruncatedSVD)", "hybrid": "Hybrid BM25 + LSA (RRF)"}


def retrieval_metrics(index: SearchIndex, questions: list[dict], method: str) -> dict:
    hit1 = hit3 = rr = 0.0
    start = time.perf_counter()
    for item in questions:
        ranked = [r["id"] for r, _ in index.search(item["q"], k=50, method=method)]
        first = next((i for i, rid in enumerate(ranked, 1) if rid in item["relevant"]), None)
        if first:
            hit1, hit3, rr = hit1 + (first == 1), hit3 + (first <= 3), rr + 1 / first
    n = len(questions)
    return {"hit@1": hit1 / n, "hit@3": hit3 / n, "mrr": rr / n, "ms": (time.perf_counter() - start) * 1000 / n}


def run() -> dict:
    spec = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    index = SearchIndex(load_investigations())
    results = {m: retrieval_metrics(index, spec["retrieval"], m) for m in METHODS}
    # A header is correct if it maps to the expected standard column (or to nothing when expected is null).
    wrong = [(h, exp) for h, exp in spec["headers"] if next(iter(match_columns([h])), None) != exp]
    results["header_accuracy"] = 1 - len(wrong) / len(spec["headers"])
    results["header_wrong"], results["n_questions"], results["n_headers"] = wrong, len(spec["retrieval"]), len(spec["headers"])
    return results


if __name__ == "__main__":
    res = run()
    print(f"Retrieval: {res['n_questions']} labelled questions\n")
    print(f"{'Method':<26}{'Hit@1':>7}{'Hit@3':>7}{'MRR':>8}{'ms/query':>10}")
    for key, label in METHODS.items():
        m = res[key]
        print(f"{label:<26}{m['hit@1']:>7.0%}{m['hit@3']:>7.0%}{m['mrr']:>8.3f}{m['ms']:>10.2f}")
    print(f"\nColumn mapping: {res['header_accuracy']:.0%} of {res['n_headers']} header variants correct")
    for header, expected in res["header_wrong"]:
        print(f"  wrong: {header!r} (expected {expected})")
