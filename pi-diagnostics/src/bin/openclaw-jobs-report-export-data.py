#!/usr/bin/env python3
"""Snapshot OpenClaw cron job statuses to the diagnostics sheet and kip-claw JSON."""
import json
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 7:
        print(
            "Usage: openclaw-jobs-export-core.py "
            "<json_path> <timestamp> <jobs_json> <state_json> <sheet_id> <gog_account>",
            file=sys.stderr,
        )
        return 2

    json_path, timestamp, jobs_path, state_path, sheet_id, gog_account = sys.argv[1:7]

    with open(jobs_path, "r", encoding="utf-8") as f:
        jobs_raw = json.load(f)
    with open(state_path, "r", encoding="utf-8") as f:
        state_raw = json.load(f)

    jobs_by_id = {j["id"]: j for j in jobs_raw.get("jobs", [])}
    states = state_raw.get("jobs", {})

    new_rows = []
    for job_id, state_obj in states.items():
        if job_id not in jobs_by_id:
            continue
        s = state_obj.get("state", {})
        name = jobs_by_id[job_id]["name"]
        status = s.get("lastRunStatus", "")
        duration_s = round(s.get("lastDurationMs", 0) / 1000, 1)
        consec_errors = s.get("consecutiveErrors", 0)
        error_reason = s.get("lastErrorReason", "")
        notes = (s.get("lastError") or "")[:200]

        new_rows.append({
            "timestamp": timestamp,
            "jobName": name,
            "status": status,
            "durationS": duration_s,
            "consecutiveErrors": consec_errors,
            "errorReason": error_reason,
            "notes": notes,
        })

        sheet_row = [
            timestamp, name, status, str(duration_s),
            str(consec_errors), error_reason, notes,
        ]
        subprocess.run(
            [
                "gog", "--no-input", "-a", gog_account,
                "sheets", "append", sheet_id, "OpenClaw Jobs!A:G",
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

    existing.extend(new_rows)
    existing.sort(key=lambda r: r.get("timestamp", ""))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    # Write current job names for heatmap filtering
    names_path = os.path.join(os.path.dirname(json_path), "cronJobNames.json")
    active_names = sorted(j["name"] for j in jobs_raw.get("jobs", []))
    with open(names_path, "w", encoding="utf-8") as f:
        json.dump(active_names, f, indent=2)

    return 0


sys.exit(main())
