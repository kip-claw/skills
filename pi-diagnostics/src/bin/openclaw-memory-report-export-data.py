#!/usr/bin/env python3
"""Snapshot OpenClaw memory index metrics to kip-claw JSON."""
import json
import os
import sys
from typing import Any


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: openclaw-memory-report-export-data.py <json_path> <timestamp> <status_json_path>",
            file=sys.stderr,
        )
        return 2

    json_path, timestamp, status_json_path = sys.argv[1:4]

    with open(status_json_path, "r", encoding="utf-8") as f:
        status_raw = json.load(f)

    if not isinstance(status_raw, list):
        raise ValueError("Expected top-level list from `openclaw memory status --deep --json`")

    rows: list[dict[str, Any]] = []
    for agent_entry in status_raw:
        if not isinstance(agent_entry, dict):
            continue

        status = agent_entry.get("status") or {}
        scan = agent_entry.get("scan") or {}
        vector = status.get("vector") or {}
        fts = status.get("fts") or {}
        cache = status.get("cache") or {}
        batch = status.get("batch") or {}
        custom = status.get("custom") or {}
        provider_state = custom.get("providerState") or {}
        audit = agent_entry.get("audit") or {}
        dreaming = agent_entry.get("dreamingAudit") or {}
        probe = agent_entry.get("embeddingProbe") or {}

        indexed_files = _safe_int(status.get("files"))
        total_files = _safe_int(scan.get("totalFiles"))
        indexed_chunks = _safe_int(status.get("chunks"))
        coverage_pct = (indexed_files / total_files * 100.0) if total_files > 0 else 0.0

        rows.append(
            {
                "timestamp": timestamp,
                "agentId": str(agent_entry.get("agentId") or "unknown"),
                "provider": str(status.get("provider") or ""),
                "model": str(status.get("model") or ""),
                "indexedFiles": indexed_files,
                "totalFiles": total_files,
                "indexedChunks": indexed_chunks,
                "coveragePct": round(coverage_pct, 2),
                "dirty": _safe_bool(status.get("dirty")),
                "embeddingsReady": _safe_bool(probe.get("ok")),
                "vectorReady": _safe_bool(vector.get("available")),
                "semanticVectorsReady": _safe_bool(vector.get("semanticAvailable")),
                "ftsReady": _safe_bool(fts.get("available")),
                "cacheEntries": _safe_int(cache.get("entries")),
                "batchEnabled": _safe_bool(batch.get("enabled")),
                "batchFailures": _safe_int(batch.get("failures")),
                "providerState": str(provider_state.get("mode") or ""),
                "indexIdentity": str((custom.get("indexIdentity") or {}).get("status") or ""),
                "recallEntries": _safe_int(audit.get("entryCount")),
                "recallPromoted": _safe_int(audit.get("promotedCount")),
                "recallSpaced": _safe_int(audit.get("spacedEntryCount")),
                "recallConceptTagged": _safe_int(audit.get("conceptTaggedEntryCount")),
                "recallUpdatedAt": str(audit.get("updatedAt") or ""),
                "dreamCorpusFiles": _safe_int(dreaming.get("sessionCorpusFileCount")),
                "dreamIngestionExists": _safe_bool(dreaming.get("sessionIngestionExists")),
            }
        )

    existing: list[dict[str, Any]] = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, list):
            raise ValueError(f"Expected list in {json_path}")
        existing = loaded

    existing.extend(rows)
    existing.sort(key=lambda r: (str(r.get("timestamp", "")), str(r.get("agentId", ""))))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    return 0


sys.exit(main())
