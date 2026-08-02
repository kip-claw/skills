#!/usr/bin/env python3
"""Export Twitter archive summary from NAS birdclaw backup to kip-claw JSON."""
import json
import os
import subprocess
import sys
from collections import defaultdict

SSH_HOST = "nas@100.118.154.80"


def ssh_read_lines(ssh_opts: list[str], path: str) -> list[str]:
    """Read a file from the NAS via SSH."""
    result = subprocess.run(
        ["ssh"] + ssh_opts + [SSH_HOST, f"cat {path}"],
        capture_output=True, text=True, timeout=120,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(f"SSH read failed for {path}: {result.stderr.strip()}")
    return result.stdout.splitlines()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: twitter-archive-export-core.py <json_path>", file=sys.stderr)
        return 2

    json_path = sys.argv[1]
    base = "/srv/dev-disk-by-uuid-a170c673-36d0-4a82-a615-e7356ef68cc6/Data/birdclaw/backup/data"
    ssh_opts = ["-i", "{{HOME}}/.ssh/nas_key", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no"]

    # 1. Get authored tweet IDs
    authored_lines = ssh_read_lines(ssh_opts, f"{base}/timeline_edges/authored.jsonl")
    authored_ids = set()
    for line in authored_lines:
        if line.strip():
            authored_ids.add(json.loads(line)["tweet_id"])

    # 2. List tweet year files
    list_result = subprocess.run(
        ["ssh"] + ssh_opts + [SSH_HOST, f"ls {base}/tweets/"],
        capture_output=True, text=True, timeout=30,
        stdin=subprocess.DEVNULL,
    )
    if list_result.returncode != 0:
        raise RuntimeError(f"Failed to list tweets dir: {list_result.stderr.strip()}")

    year_files = sorted(f.strip() for f in list_result.stdout.splitlines() if f.strip().endswith(".jsonl"))

    # 3. Read tweets, filter to authored.
    #
    # Older JSONL backups identify authored tweets only through the authored
    # timeline edge.  Live-sync records are written with the stable local
    # ``profile_me`` author id, but the edge export can lag behind them.  Use
    # both signals so a stale edge file cannot make the public report stale.
    tweets = []
    for fname in year_files:
        lines = ssh_read_lines(ssh_opts, f"{base}/tweets/{fname}")
        for line in lines:
            if not line.strip():
                continue
            t = json.loads(line)
            if t["id"] in authored_ids or t.get("author_profile_id") == "profile_me":
                tweets.append(t)

    # 4. Build monthly counts
    monthly: dict[str, int] = defaultdict(int)
    for t in tweets:
        if t.get("created_at"):
            month = t["created_at"][:7]
            monthly[month] += 1

    # 5. Top 10 by like_count
    top_tweets = sorted(tweets, key=lambda t: t.get("like_count", 0), reverse=True)[:10]

    # 6. Summary stats
    total = len(tweets)
    dates = [t["created_at"] for t in tweets if t.get("created_at")]
    first_date = min(dates, default="")
    last_date = max(dates, default="")
    total_likes = sum(t.get("like_count", 0) for t in tweets)
    reply_count = sum(1 for t in tweets if t.get("reply_to_id"))
    original_count = total - reply_count

    output = {
        "summary": {
            "totalTweets": total,
            "totalLikes": total_likes,
            "originalTweets": original_count,
            "replies": reply_count,
            "firstTweet": first_date,
            "lastTweet": last_date,
        },
        "monthlyTweets": [{"month": k, "count": v} for k, v in sorted(monthly.items())],
        "topTweets": [{
            "id": t["id"],
            "text": t["text"],
            "createdAt": t.get("created_at", ""),
            "likeCount": t.get("like_count", 0),
            "mediaCount": t.get("media_count", 0),
            "isReply": bool(t.get("reply_to_id")),
            "media": [m["url"] for m in json.loads(t.get("media_json", "[]")) if m.get("url")],
        } for t in top_tweets],
    }

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"Wrote {total} tweets ({len(monthly)} months, {len(top_tweets)} top)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
