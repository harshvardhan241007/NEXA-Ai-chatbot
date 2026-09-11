"""
Minimal Retrieval-Augmented Generation (RAG) module.

Deliberately dependency-light: it builds a plain TF-IDF index with
numpy (no sklearn / no paid embedding API required), so document Q&A
works even in local-fallback mode with zero API keys configured.
Retrieved chunks are then optionally handed to the LLM as context.
"""

import re
import math
from collections import Counter
from typing import List, Tuple

import numpy as np

from .logger import get_logger

log = get_logger(__name__)

_WORD_RE = re.compile(r"[a-zA-Z0-9']+")


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Split text into overlapping character chunks on paragraph-ish
    boundaries so each chunk stays reasonably self-contained."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == length:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


class TfidfIndex:
    """Tiny TF-IDF index over a list of text chunks."""

    def __init__(self, chunks: List[str]):
        self.chunks = chunks
        self._vocab = {}
        self._doc_vectors = None
        self._idf = None
        if chunks:
            self._build()

    def _build(self) -> None:
        tokenized_docs = [_tokenize(c) for c in self.chunks]

        vocab = sorted({tok for doc in tokenized_docs for tok in doc})
        self._vocab = {tok: i for i, tok in enumerate(vocab)}
        n_docs = len(tokenized_docs)
        n_terms = len(vocab)

        # document frequency
        df = np.zeros(n_terms)
        for doc in tokenized_docs:
            for tok in set(doc):
                df[self._vocab[tok]] += 1
        self._idf = np.log((1 + n_docs) / (1 + df)) + 1.0

        matrix = np.zeros((n_docs, n_terms))
        for i, doc in enumerate(tokenized_docs):
            counts = Counter(doc)
            total = max(len(doc), 1)
            for tok, cnt in counts.items():
                tf = cnt / total
                matrix[i, self._vocab[tok]] = tf * self._idf[self._vocab[tok]]

        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self._doc_vectors = matrix / norms

    def _vectorize_query(self, query: str) -> np.ndarray:
        vec = np.zeros(len(self._vocab))
        tokens = _tokenize(query)
        counts = Counter(tokens)
        total = max(len(tokens), 1)
        for tok, cnt in counts.items():
            if tok in self._vocab:
                idx = self._vocab[tok]
                vec[idx] = (cnt / total) * self._idf[idx]
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if self._doc_vectors is None or len(self.chunks) == 0:
            return []
        q_vec = self._vectorize_query(query)
        scores = self._doc_vectors @ q_vec
        top_idx = np.argsort(-scores)[:top_k]
        return [(self.chunks[i], float(scores[i])) for i in top_idx if scores[i] > 0]


class DocumentStore:
    """Keeps one TF-IDF index per session so multiple users/uploads
    don't collide."""

    def __init__(self):
        self._indexes = {}

    def add_document(self, session_id: str, text: str) -> int:
        chunks = chunk_text(text)
        self._indexes[session_id] = TfidfIndex(chunks)
        log.info("Indexed %d chunks for session %s", len(chunks), session_id)
        return len(chunks)

    def has_document(self, session_id: str) -> bool:
        return session_id in self._indexes and len(self._indexes[session_id].chunks) > 0

    def retrieve(self, session_id: str, query: str, top_k: int = 3) -> List[str]:
        index = self._indexes.get(session_id)
        if not index:
            return []
        return [chunk for chunk, _score in index.search(query, top_k=top_k)]


# Process-wide singleton store (fine for a single-process dev/demo server;
# swap for a persistent vector DB in production).
document_store = DocumentStore()
