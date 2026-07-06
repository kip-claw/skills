#!/usr/bin/env python3
"""Export a semantic-space snapshot from OpenClaw memory embeddings."""

import json
import math
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from typing import Any

import numpy as np


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "been",
    "before",
    "being",
    "between",
    "could",
    "first",
    "from",
    "have",
    "into",
    "just",
    "like",
    "made",
    "make",
    "many",
    "more",
    "most",
    "much",
    "only",
    "other",
    "over",
    "same",
    "some",
    "such",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "very",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
}

LABEL_EXCLUDE = STOPWORDS | {
    "assistant",
    "candidate",
    "chat",
    "conversation",
    "cron",
    "dreaming",
    "home",
    "label",
    "memory",
    "message",
    "metadata",
    "sender",
    "session",
    "status",
    "timestamp",
    "untrusted",
    "user",
    "welsh",
    "ben",
}

TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")
BASIC_WORDS = {
    "json",
    "http",
    "https",
    "com",
    "org",
    "www",
    "tmp",
    "null",
    "true",
    "false",
}

NOISE_PATTERNS = [
    re.compile(r"```json.*?```", re.IGNORECASE | re.DOTALL),
    re.compile(r"Conversation info \(untrusted metadata\):", re.IGNORECASE),
    re.compile(r"Sender \(untrusted metadata\):", re.IGNORECASE),
    re.compile(r"Session Key:\s*[^\n]+", re.IGNORECASE),
    re.compile(r"Session ID:\s*[^\n]+", re.IGNORECASE),
    re.compile(r"timestamp\s*:\s*[^\n]+", re.IGNORECASE),
]

CRON_SENDER_PATTERNS = [
    re.compile(r'"sender"\s*:\s*"cron(?:\b|[^"]*)"', re.IGNORECASE),
    re.compile(r'"sender_id"\s*:\s*"cron(?:\b|[^"]*)"', re.IGNORECASE),
    re.compile(r'"label"\s*:\s*"cron(?:\b|[^"]*)"', re.IGNORECASE),
    re.compile(r'Sender \(untrusted metadata\).*?"label"\s*:\s*"cron', re.IGNORECASE | re.DOTALL),
]


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _kmeans(points: np.ndarray, k: int, seed: int = 42, steps: int = 20) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = points.shape[0]
    if n == 0:
        return np.array([], dtype=np.int32)

    k = max(1, min(k, n))
    init_idx = rng.choice(n, size=k, replace=False)
    centroids = points[init_idx].copy()
    labels = np.zeros(n, dtype=np.int32)

    for _ in range(steps):
        distances = ((points[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        next_labels = distances.argmin(axis=1).astype(np.int32)

        if np.array_equal(labels, next_labels):
            break
        labels = next_labels

        for idx in range(k):
            members = points[labels == idx]
            if len(members) == 0:
                centroids[idx] = points[rng.integers(0, n)]
            else:
                centroids[idx] = members.mean(axis=0)

    return labels


def _cluster_label_tokens(texts: list[str]) -> list[str]:
    counter: Counter[str] = Counter()
    for text in texts:
        for token in re.findall(r"[a-zA-Z]{4,}", text.lower()):
            if token in STOPWORDS:
                continue
            counter[token] += 1

    return [token for token, _ in counter.most_common(12) if token not in LABEL_EXCLUDE]


def _cluster_description(tokens: list[str], title: str) -> str:
    title_lc = title.lower()
    detail_tokens = [token for token in tokens if token.lower() != title_lc][:3]
    if not detail_tokens:
        return "General memory topics"
    return ", ".join(token.title() for token in detail_tokens)


def _tokenize(text: str) -> list[str]:
    for pattern in NOISE_PATTERNS:
        text = pattern.sub(" ", text)

    tokens = []
    for token in TOKEN_RE.findall(text.lower()):
        if token in STOPWORDS or token in LABEL_EXCLUDE or token in BASIC_WORDS:
            continue
        tokens.append(token)
    return tokens


def _cluster_keywords_ctfidf(cluster_texts: dict[int, list[str]]) -> dict[int, list[str]]:
    """Compute BERTopic-style c-TF-IDF keywords per cluster using simple token stats.

    c-TF-IDF intuition:
    - Treat each cluster as a single document.
    - Weight terms that are frequent in one cluster but not common across clusters.
    """
    cluster_term_counts: dict[int, Counter[str]] = {}
    cluster_totals: dict[int, int] = {}
    doc_freq: Counter[str] = Counter()

    for cid, texts in cluster_texts.items():
        counts: Counter[str] = Counter()
        for text in texts:
            tokens = _tokenize(text)
            counts.update(tokens)
            # Add lightweight bigrams to improve topical specificity.
            for i in range(len(tokens) - 1):
                bigram = f"{tokens[i]}_{tokens[i + 1]}"
                counts[bigram] += 1

        cluster_term_counts[cid] = counts
        cluster_totals[cid] = sum(counts.values())
        for term in counts.keys():
            doc_freq[term] += 1

    cluster_count = max(1, len(cluster_texts))
    keywords: dict[int, list[str]] = {}

    for cid, counts in cluster_term_counts.items():
        total = max(1, cluster_totals[cid])
        scored: list[tuple[str, float]] = []
        for term, count in counts.items():
            # c-TF component: cluster-normalized term frequency.
            ctf = count / total
            # IDF component across cluster-documents.
            idf = math.log((cluster_count + 1) / (doc_freq[term] + 1)) + 1.0
            score = ctf * idf
            scored.append((term, score))

        scored.sort(key=lambda item: item[1], reverse=True)

        # Prefer readable terms: avoid mixed punctuation; keep unigrams + useful bigrams.
        selected: list[str] = []
        for term, _ in scored:
            plain = term.replace("_", " ")
            if len(plain) < 4:
                continue
            if any(ch.isdigit() for ch in plain):
                continue
            if plain in selected:
                continue
            selected.append(plain)
            if len(selected) >= 8:
                break

        keywords[cid] = selected

    return keywords


def _is_cron_sender_chunk(text: str) -> bool:
    for pattern in CRON_SENDER_PATTERNS:
        if pattern.search(text):
            return True
    return False


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: openclaw-memory-map-export-data.py <json_path> <timestamp> <sqlite_path>",
            file=sys.stderr,
        )
        return 2

    json_path, timestamp, sqlite_path = sys.argv[1:4]

    conn = sqlite3.connect(sqlite_path)
    rows = conn.execute(
        """
        select id, path, source, text, embedding
        from memory_index_chunks
        where embedding is not null and source = 'memory'
        """
    ).fetchall()
    conn.close()

    records: list[dict[str, Any]] = []
    excluded_cron_chunks = 0
    for chunk_id, path, source, text, embedding_json in rows:
        text = str(text or "")
        if _is_cron_sender_chunk(text):
            excluded_cron_chunks += 1
            continue
        if not embedding_json:
            continue
        try:
            vector = np.array(json.loads(embedding_json), dtype=np.float32)
        except Exception:
            continue
        if vector.ndim != 1 or vector.size < 2:
            continue
        records.append(
            {
                "chunkId": str(chunk_id),
                "path": str(path or ""),
                "source": str(source or ""),
                "text": text,
                "vector": vector,
            }
        )

    if not records:
        payload = {
            "timestamp": timestamp,
            "method": "pca2+kmeans",
            "pointCount": 0,
            "clusterCount": 0,
            "excludedCronChunks": excluded_cron_chunks,
            "clusters": [],
            "points": [],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return 0

    max_points = 700
    if len(records) > max_points:
        rng = np.random.default_rng(42)
        keep = np.sort(rng.choice(len(records), size=max_points, replace=False))
        records = [records[i] for i in keep]

    matrix = np.stack([r["vector"] for r in records])
    centered = matrix - matrix.mean(axis=0)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ vt[:2].T

    std = projected.std(axis=0)
    std[std == 0] = 1.0
    projected = projected / std

    n = projected.shape[0]
    k = int(max(3, min(8, round(math.sqrt(n / 18)))))
    labels = _kmeans(projected, k=k)

    cluster_texts: dict[int, list[str]] = defaultdict(list)
    for idx, rec in enumerate(records):
        cluster_texts[int(labels[idx])].append(rec["text"])

    cluster_sizes = Counter(int(x) for x in labels.tolist())
    keyword_map = _cluster_keywords_ctfidf(cluster_texts)
    clusters = []
    used_labels: set[str] = set()
    for cid, size in sorted(cluster_sizes.items(), key=lambda item: item[1], reverse=True):
        tokens = keyword_map.get(cid, [])
        base_label = tokens[0].title() if tokens else "General"
        label = base_label
        if label in used_labels:
            alt = next((token.title() for token in tokens[1:] if token.title() not in used_labels), None)
            if alt:
                label = alt
            else:
                suffix = 2
                while f"{base_label}{suffix}" in used_labels:
                    suffix += 1
                label = f"{base_label}{suffix}"
        used_labels.add(label)

        clusters.append(
            {
                "id": cid,
                "label": label,
                "description": _cluster_description(tokens, label),
                "keywords": tokens[:6],
                "size": int(size),
            }
        )

    points = []
    for idx, rec in enumerate(records):
        x, y = projected[idx]
        points.append(
            {
                "x": round(_safe_float(x), 4),
                "y": round(_safe_float(y), 4),
                "cluster": int(labels[idx]),
                "path": rec["path"],
                "source": rec["source"],
            }
        )

    payload = {
        "timestamp": timestamp,
        "method": "pca2+kmeans",
        "pointCount": len(points),
        "clusterCount": len(clusters),
        "excludedCronChunks": excluded_cron_chunks,
        "clusters": clusters,
        "points": points,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return 0


sys.exit(main())
