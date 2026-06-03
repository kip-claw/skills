#!/usr/bin/env python3
"""Snapshot OpenClaw config metadata to the diagnostics sheet and kip-claw JSON."""
import json
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 7:
        print(
            "Usage: openclaw-config-export-core.py "
            "<json_path> <timestamp> <openclaw_json> <update_check_json> <sheet_id> <gog_account>",
            file=sys.stderr,
        )
        return 2

    json_path, timestamp, config_path, update_path, sheet_id, gog_account = sys.argv[1:7]

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(update_path, "r", encoding="utf-8") as f:
        upd = json.load(f)

    # Prefer installed/runtime version recorded in config metadata.
    # Fallback to update notifier version for compatibility with older files.
    version = cfg.get("meta", {}).get("lastTouchedVersion", "") or upd.get("lastNotifiedVersion", "")
    defaults = cfg.get("agents", {}).get("defaults", {})
    primary_model = defaults.get("model", {}).get("primary", "")
    runtime = defaults.get("agentRuntime", {}).get("id", "")
    mem = defaults.get("memorySearch", {})
    mem_provider = mem.get("provider", "")
    mem_model = mem.get("model", "")
    skills_count = len(defaults.get("skills", []))
    gateway_mode = cfg.get("gateway", {}).get("mode", "")

    row = {
        "timestamp": timestamp,
        "version": version,
        "primaryModel": primary_model,
        "agentRuntime": runtime,
        "memSearchProvider": mem_provider,
        "memSearchModel": mem_model,
        "skillsCount": skills_count,
        "gatewayMode": gateway_mode,
        "notes": "",
    }
    sheet_row = [
        timestamp, version, primary_model, runtime,
        mem_provider, mem_model, str(skills_count), gateway_mode, "",
    ]

    subprocess.run(
        [
            "gog", "--no-input", "-a", gog_account,
            "sheets", "append", sheet_id, "OpenClaw Config!A:I",
            "--values-json", json.dumps([sheet_row]),
            "--insert", "INSERT_ROWS",
        ],
        check=True,
        env=os.environ.copy(),
        stdin=subprocess.DEVNULL,
        timeout=60,
    )

    existing: list = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if not isinstance(existing, list):
            raise ValueError(f"Expected list in {json_path}")

    existing.append(row)
    existing.sort(key=lambda r: r.get("timestamp", ""))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    return 0


sys.exit(main())
