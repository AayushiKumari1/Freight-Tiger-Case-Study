"""A tiny, dependency-free TF-IDF vector index over the notes.

Why not an embedding model / vector DB? With 10 short notes, a metadata filter does the heavy lifting
and TF-IDF is enough to rank what is left. It is also fully deterministic (no model download, no
randomness) and free. `Retriever` is the single seam: swap in an embedding model behind the same
`search()` signature if the notes corpus grows.
"""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"a", "an", "the", "of", "on", "in", "to", "and", "or", "for", "by", "was", "were", "is", "are",
         "this", "that", "with", "as", "at", "from", "after", "be", "no", "not"}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


class Retriever:
    def __init__(self, docs: dict[str, str]):
        self.ids = sorted(docs)
        tokens = {i: tokenize(docs[i]) for i in self.ids}
        n = len(self.ids)
        df = Counter(t for toks in tokens.values() for t in set(toks))
        self.idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self.vecs = {i: self._vectorise(tokens[i]) for i in self.ids}

    def _vectorise(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        vec = {t: c * self.idf.get(t, 0.0) for t, c in tf.items() if t in self.idf}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, restrict_to: set[str] | None = None, k: int = 5) -> list[tuple[str, float]]:
        """Top-k (note_id, cosine) among `restrict_to`; ties broken by note_id so order is stable."""
        q = self._vectorise(tokenize(query))
        scored = []
        for i in self.ids:
            if restrict_to is not None and i not in restrict_to:
                continue
            d = self.vecs[i]
            scored.append((i, sum(w * d.get(t, 0.0) for t, w in q.items())))
        scored.sort(key=lambda x: (-round(x[1], 12), x[0]))
        return scored[:k]
