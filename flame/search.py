"""Hybrid search: BM25 (keywords) + LSA (meaning) fused with Reciprocal Rank Fusion.

* BM25 - classic search-engine ranking: rewards rare query words, saturates repeated words, normalises length.
* LSA  - Latent Semantic Analysis: TF-IDF vectors compressed with TruncatedSVD, so documents using related
         words ("extinguish" / "suppression") end up close together.
* RRF  - Reciprocal Rank Fusion: score = sum over rankers of 1 / (k + rank). Merges rankings without having
         to calibrate their very different score scales.
"""
import math
import re
from collections import Counter

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from flame.data import record_text

RRF_K = 60  # standard constant from the original RRF paper (Cormack et al., 2009)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in ENGLISH_STOP_WORDS]


class BM25:
    """Okapi BM25 with the usual parameters k1=1.5, b=0.75."""

    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / len(self.docs)
        df = Counter(word for d in self.docs for word in d)
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> np.ndarray:
        out = np.zeros(len(self.docs))
        for w in set(tokenize(query)) & self.idf.keys():
            for i, d in enumerate(self.docs):
                tf = d.get(w, 0)
                norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg_len)
                out[i] += self.idf[w] * tf * (self.k1 + 1) / (tf + norm)
        return out


class VectorRanker:
    """TF-IDF + cosine similarity. With `dims`, the vectors are first reduced by TruncatedSVD = LSA."""

    def __init__(self, texts: list[str], dims: int | None = None):
        self.vec = TfidfVectorizer(stop_words="english", sublinear_tf=True, ngram_range=(1, 1 if dims else 2))
        matrix = self.vec.fit_transform(texts)
        self.svd = TruncatedSVD(min(dims, len(texts) - 1), random_state=0) if dims else None
        self.matrix = self.svd.fit_transform(matrix) if self.svd else matrix

    def scores(self, query: str) -> np.ndarray:
        q = self.vec.transform([query])
        return cosine_similarity(self.svd.transform(q) if self.svd else q, self.matrix)[0]


def rrf(rankings: list[np.ndarray], k: int = RRF_K) -> np.ndarray:
    """Fuse several score arrays by rank. Items a ranker scores 0 get no credit from it."""
    fused = np.zeros(len(rankings[0]))
    for scores in rankings:
        for rank, i in enumerate(np.argsort(-scores), start=1):
            if scores[i] > 0:
                fused[i] += 1 / (k + rank)
    return fused


class HybridIndex:
    """One searchable collection. method = 'hybrid' (default), 'bm25', 'lsa' or 'tfidf' (baseline)."""

    def __init__(self, items: list, texts: list[str]):
        self.items, self.rankers = items, {}
        if texts:
            self.rankers = {"bm25": BM25(texts), "tfidf": VectorRanker(texts)}
        if len(texts) >= 3:  # SVD needs a few documents to find latent topics
            self.rankers["lsa"] = VectorRanker(texts, dims=16)

    def scores(self, query: str, method: str) -> np.ndarray:
        if method != "hybrid":
            return self.rankers[method].scores(query)
        parts = [self.rankers[m].scores(query) for m in ("bm25", "lsa") if m in self.rankers]
        return rrf(parts) if len(parts) > 1 else parts[0]

    def search(self, query: str, k: int = 5, method: str = "hybrid") -> list[tuple]:
        """Top-k (item, score) pairs with score > 0. Hybrid scores are RRF values (max ~0.033)."""
        if not self.rankers or not query.strip():
            return []
        s = self.scores(query, method)
        return [(self.items[i], float(s[i])) for i in np.argsort(-s)[:k] if s[i] > 0]


class SearchIndex:
    """Investigation records + text passages from imported documents, each with its own hybrid index."""

    def __init__(self, records: list[dict], documents: list[dict] = ()):
        self.records = HybridIndex(records, [record_text(r) for r in records])
        self.docs = HybridIndex(list(documents), [f"{d['title']} {d['text']}" for d in documents])

    def search(self, query: str, k: int = 5, method: str = "hybrid") -> list[tuple[dict, float]]:
        return self.records.search(query, k, method)

    def search_docs(self, query: str, k: int = 3) -> list[tuple[dict, float]]:
        return self.docs.search(query, k)
