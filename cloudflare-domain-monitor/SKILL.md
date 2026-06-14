---
name: cloudflare-domain-monitor
description: Monitors Ben's domains and logs their DNS, ping, HTTPS, and TLS status.
tag: Monitoring
---

# Domain Monitor (Cloudflare + External)

Use this skill for requests about checking, logging, exporting, or reporting status for Ben's monitored domains.

## Command

```bash
{{HOME}}/bin/cloudflare-domain-monitor-runner.sh
```

The command:

- Lists Cloudflare zones using `CLOUDFLARE_API_TOKEN`.
- Loads extra non-Cloudflare domains from:

```bash
{{HOME}}/.openclaw/workspace/skills/cloudflare-domain-monitor/config/manual-domains.json
```

- Checks each apex domain with public network probes:
  - DNS resolution
  - ICMP ping reachability and average latency
  - HTTPS status code, response time, final URL, and remote IP
  - TLS certificate expiration days
- Appends rows to the Google Sheet configured in `CLOUDFLARE_DOMAINS_SHEET_ID`.
- Updates `{{HOME}}/Code/kip-claw/static/data/cloudflareDomains.json`.
- Commits and pushes the JSON update in `{{HOME}}/Code/kip-claw`.

## Sheet

Google Sheet:

```text
https://docs.google.com/spreadsheets/d/1w0AuMDNvXJx7KanhlXE7tr1RVQS6Z32-_F3qX80YqII/edit
```

It has a `Checks` tab.

Header row:

```text
Timestamp | Domain | Zone Status | Paused | Plan | DNS OK | IPs | Ping OK | Ping Avg (ms) | HTTPS OK | HTTP Status | Response (ms) | TLS Days Left | Final URL | Remote IP | Error
```

The sheet ID is stored in `{{HOME}}/.openclaw/.env`:

```bash
CLOUDFLARE_DOMAINS_SHEET_ID="1w0AuMDNvXJx7KanhlXE7tr1RVQS6Z32-_F3qX80YqII"
```

## Site Data Export

The public JSON file is:

```bash
{{HOME}}/Code/kip-claw/static/data/cloudflareDomains.json
```

Shape:

- `generatedAt`: ISO timestamp for the latest run
- `summary`: total domains, ok domains, warning domains, failing domains
- `domains`: latest check per domain
- `history`: recent historical checks, capped by the collector

Each row also includes:

- `source`: `cloudflare` or `manual`
- `provider`: provider hint (for example `cloudflare`, `namecheap`)

## Reporting

When reporting results to Ben, lead with failures or warnings, then summarize:

- number of domains checked
- domains failing DNS, HTTPS, TLS, or ping
- domains with TLS certificates expiring within 30 days
- whether the Google Sheet append and kip.computer JSON export succeeded

Do not edit DNS records, Cloudflare settings, or R2 objects from this skill unless Ben explicitly approves the exact change.

## Cron

Recommended cadence: every 6 hours, staggered away from other health jobs.

Example:

```cron
17 */6 * * * {{HOME}}/bin/cloudflare-domain-monitor-runner.sh
```

## Publish Decision

This is a publish candidate after sanitizing:

- Remove Ben-specific sheet IDs if any are added.
- Keep paths generic or document them as local deployment examples.
- Do not include tokens, account IDs, zone IDs, or private hostnames beyond public domain names already returned by Cloudflare.
