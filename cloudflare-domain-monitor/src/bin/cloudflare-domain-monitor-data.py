#!/usr/bin/env python3
"""Collect Cloudflare domain status checks for Kip."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any


HEADERS = [
    "Timestamp",
    "Domain",
    "Zone Status",
    "Paused",
    "Plan",
    "DNS OK",
    "IPs",
    "Ping OK",
    "Ping Avg (ms)",
    "HTTPS OK",
    "HTTP Status",
    "Response (ms)",
    "TLS Days Left",
    "Final URL",
    "Remote IP",
    "Error",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def cloudflare_get(path: str, token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Cloudflare API HTTP {exc.code}: {body}") from exc
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare API error: {data.get('errors')}")
    return data


def list_zones(token: str) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    page = 1
    while True:
        data = cloudflare_get(f"/zones?per_page=50&page={page}", token)
        zones.extend(data.get("result", []))
        info = data.get("result_info") or {}
        if page >= int(info.get("total_pages") or 1):
            break
        page += 1
    return sorted(zones, key=lambda z: z.get("name", ""))


def dns_check(domain: str) -> tuple[bool, list[str], str]:
    try:
        infos = socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        return False, [], str(exc)
    ips = sorted({item[4][0] for item in infos})
    return bool(ips), ips, ""


def ping_check(domain: str) -> tuple[bool, float | None, str]:
    try:
        proc = subprocess.run(
            ["ping", "-c", "2", "-W", "2", domain],
            text=True,
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, None, str(exc)

    output = f"{proc.stdout}\n{proc.stderr}"
    match = re.search(r"=\s*[\d.]+/([\d.]+)/[\d.]+/[\d.]+\s*ms", output)
    avg = float(match.group(1)) if match else None
    if proc.returncode == 0:
        return True, avg, ""
    return False, avg, "ping failed"


def https_check(domain: str) -> tuple[bool, int | None, float | None, str, str, str]:
    write_out = "\t".join(
        ["%{http_code}", "%{time_total}", "%{url_effective}", "%{remote_ip}", "%{ssl_verify_result}"]
    )
    try:
        proc = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--location",
                "--output",
                "/dev/null",
                "--max-time",
                "20",
                "--write-out",
                write_out,
                f"https://{domain}/",
            ],
            text=True,
            capture_output=True,
            timeout=25,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, None, None, "", "", str(exc)

    parts = proc.stdout.strip().split("\t")
    http_status: int | None = None
    response_ms: float | None = None
    final_url = ""
    remote_ip = ""
    ssl_verify = "1"
    if len(parts) == 5:
        http_status = int(parts[0]) if parts[0].isdigit() else None
        response_ms = round(float(parts[1]) * 1000, 1) if parts[1] else None
        final_url = parts[2]
        remote_ip = parts[3]
        ssl_verify = parts[4]

    ok = (
        proc.returncode == 0
        and ssl_verify == "0"
        and http_status is not None
        and 200 <= http_status < 400
    )
    error = proc.stderr.strip()
    if proc.returncode != 0 and not error:
        error = f"curl exit {proc.returncode}"
    if ssl_verify != "0":
        error = f"{error}; ssl verify result {ssl_verify}".strip("; ")
    return ok, http_status, response_ms, final_url, remote_ip, error


def tls_days_left(domain: str) -> tuple[int | None, str]:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((domain, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
    except OSError as exc:
        return None, str(exc)
    not_after = cert.get("notAfter")
    if not not_after:
        return None, "missing notAfter"
    expiry = parsedate_to_datetime(not_after)
    days = int((expiry - utc_now()).total_seconds() // 86400)
    return days, ""


def status_for(row: dict[str, Any]) -> str:
    if row["zoneStatus"] != "active" or row["paused"]:
        return "fail"
    if not row["dnsOk"] or not row["httpsOk"]:
        return "fail"
    if row["tlsDaysLeft"] is not None and row["tlsDaysLeft"] < 14:
        return "fail"
    if not row["pingOk"]:
        return "warn"
    if row["tlsDaysLeft"] is not None and row["tlsDaysLeft"] < 30:
        return "warn"
    return "ok"


def collect_domain(timestamp: str, zone: dict[str, Any]) -> dict[str, Any]:
    domain = zone.get("name", "")
    errors: list[str] = []
    dns_ok, ips, dns_error = dns_check(domain)
    if dns_error:
        errors.append(f"dns: {dns_error}")

    ping_ok, ping_avg_ms, ping_error = ping_check(domain)
    if ping_error:
        errors.append(f"ping: {ping_error}")

    https_ok, http_status, response_ms, final_url, remote_ip, https_error = https_check(domain)
    if https_error:
        errors.append(f"https: {https_error}")

    tls_left, tls_error = tls_days_left(domain)
    if tls_error:
        errors.append(f"tls: {tls_error}")

    row = {
        "timestamp": timestamp,
        "domain": domain,
        "zoneStatus": zone.get("status", ""),
        "paused": bool(zone.get("paused", False)),
        "plan": ((zone.get("plan") or {}).get("name") or ""),
        "dnsOk": dns_ok,
        "ips": ips,
        "pingOk": ping_ok,
        "pingAvgMs": ping_avg_ms,
        "httpsOk": https_ok,
        "httpStatus": http_status,
        "responseMs": response_ms,
        "tlsDaysLeft": tls_left,
        "finalUrl": final_url,
        "remoteIp": remote_ip,
        "error": "; ".join(errors),
    }
    row["status"] = status_for(row)
    return row


def row_key(row: dict[str, Any]) -> str:
    return f"{row.get('timestamp')}|{row.get('domain')}"


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            return []
        data = json.loads(text)
    except (OSError, json.JSONDecodeError):
        # Existing file is missing, empty, or corrupt — start a fresh history.
        return []
    history = data.get("history", []) if isinstance(data, dict) else data
    return [row for row in history if isinstance(row, dict)]


def build_export(timestamp: str, latest: list[dict[str, Any]], history: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "total": len(latest),
        "ok": sum(1 for row in latest if row.get("status") == "ok"),
        "warn": sum(1 for row in latest if row.get("status") == "warn"),
        "fail": sum(1 for row in latest if row.get("status") == "fail"),
    }
    return {
        "generatedAt": timestamp,
        "summary": summary,
        "domains": latest,
        "history": history,
    }


def values_json(latest: list[dict[str, Any]]) -> list[list[Any]]:
    rows = []
    for row in latest:
        rows.append(
            [
                row["timestamp"],
                row["domain"],
                row["zoneStatus"],
                row["paused"],
                row["plan"],
                row["dnsOk"],
                ", ".join(row["ips"]),
                row["pingOk"],
                row["pingAvgMs"],
                row["httpsOk"],
                row["httpStatus"],
                row["responseMs"],
                row["tlsDaysLeft"],
                row["finalUrl"],
                row["remoteIp"],
                row["error"],
            ]
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-path", required=True)
    parser.add_argument("--values-json-path", required=True)
    parser.add_argument("--summary-path", required=True)
    parser.add_argument("--max-history", type=int, default=2000)
    args = parser.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not token:
        print("CLOUDFLARE_API_TOKEN is not set", file=sys.stderr)
        return 2

    timestamp = isoformat(utc_now())
    zones = list_zones(token)
    latest = [collect_domain(timestamp, zone) for zone in zones]

    json_path = Path(args.json_path)
    existing = load_existing(json_path)
    keyed = {row_key(row): row for row in existing}
    for row in latest:
        keyed[row_key(row)] = row
    history = sorted(keyed.values(), key=lambda row: (row.get("timestamp", ""), row.get("domain", "")))
    if len(history) > args.max_history:
        history = history[-args.max_history :]

    export = build_export(timestamp, latest, history)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(export, indent=2) + "\n", encoding="utf-8")

    values_path = Path(args.values_json_path)
    values_path.parent.mkdir(parents=True, exist_ok=True)
    values_path.write_text(json.dumps(values_json(latest)), encoding="utf-8")

    summary_path = Path(args.summary_path)
    summary_path.write_text(json.dumps(export["summary"], sort_keys=True), encoding="utf-8")

    print(
        f"checked={export['summary']['total']} ok={export['summary']['ok']} "
        f"warn={export['summary']['warn']} fail={export['summary']['fail']}"
    )
    return 0


if __name__ == "__main__":
    started = time.monotonic()
    try:
        raise SystemExit(main())
    finally:
        _ = time.monotonic() - started
