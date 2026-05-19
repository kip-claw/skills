---
name: openclaw-upstream-pr
description: Guide for submitting pull requests to the openclaw/openclaw upstream repository. Use when proposing bug fixes, features, or patches to OpenClaw maintainers.
metadata: {"openclaw": {"emoji": "🦞"}}
---

# OpenClaw Upstream Pull Request

Workflow for creating and submitting pull requests to the `openclaw/openclaw` GitHub repository from the `kip-claw/openclaw` fork.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated as `kip-claw`
- SSH key at `~/.ssh/id_ed25519` configured for GitHub
- PAT stored in `~/.openclaw/.env` as `GITHUB_PAT`

```bash
source ~/.openclaw/.env && export GH_TOKEN="$GITHUB_PAT"
```

## Fork Setup

The fork lives at `kip-claw/openclaw`. Clone it to a temporary working directory:

```bash
git clone git@github.com:kip-claw/openclaw.git /tmp/openclaw-patch
cd /tmp/openclaw-patch
git remote add upstream git@github.com:openclaw/openclaw.git
git fetch upstream
git checkout -b fix/descriptive-branch-name upstream/main
```

## Source Layout

Key directories in the OpenClaw source:

| Path | Purpose |
|------|---------|
| `src/cron/` | Cron scheduler, timers, watchdogs |
| `src/config/` | Configuration types and loaders |
| `src/agent/` | Agent runtime, embedded sessions |
| `src/gateway/` | Gateway server, routing |
| `src/delivery/` | Message delivery (telegram, etc.) |
| `src/logging/` | Diagnostics, liveness, phases |

TypeScript source compiles to `dist/` as bundled JS files (e.g., `dist/server-cron-*.js`).

## Workflow

### 1. Identify the Problem in Production

Reproduce the issue on the local Pi 5 instance. Gather evidence:

```bash
# Journal logs with timestamps
sudo journalctl -u openclaw --since "1 hour ago" --no-pager | grep -i "error\|timeout\|abort"

# Cron job state
openclaw cron list 2>&1
openclaw cron get <job-id> 2>&1
```

### 2. Find the Relevant Source

Locate the compiled runtime to understand the code path:

```bash
# Find compiled modules
ls /usr/lib/node_modules/openclaw/dist/

# Search for constants/functions
grep -n "RELEVANT_CONSTANT" /usr/lib/node_modules/openclaw/dist/*.js
```

Then find the corresponding TypeScript source in the fork:

```bash
cd /tmp/openclaw-patch
grep -rn "RELEVANT_CONSTANT" src/
```

### 3. Validate the Fix Locally First

Patch the compiled JS in production to confirm the fix works before writing the PR:

```bash
# Edit the compiled file
sudo nano /usr/lib/node_modules/openclaw/dist/server-cron-*.js

# Clear Node compile cache (CRITICAL — stale bytecode will mask your patch)
sudo rm -rf /var/tmp/openclaw-compile-cache

# Restart the gateway
sudo systemctl restart openclaw

# Test
openclaw cron run <job-id>
sudo journalctl -u openclaw -f
```

### 4. Write the TypeScript Fix

Apply the equivalent change in the fork's TypeScript source:

```bash
cd /tmp/openclaw-patch
# Edit the relevant .ts files
# Follow existing code patterns (naming, exports, config structure)
```

**Conventions observed:**
- Constants use `SCREAMING_SNAKE_CASE`
- Config resolution functions follow `resolve<PropertyName>()` pattern
- Optional config fields use `property?: type` in interface definitions
- Watchdog/timeout values should be configurable via `CronConfig` when possible

### 5. Run Tests Before Committing

```bash
cd /tmp/openclaw-patch
pnpm build && pnpm check && pnpm test
```

For extension/plugin changes, use fast targeted lanes first:
```bash
pnpm test:extension <extension-name>
pnpm test:contracts
```

If you changed bundled-plugin boundaries:
```bash
node scripts/check-src-extension-import-boundary.mjs --json
node scripts/check-sdk-package-extension-import-boundary.mjs --json
```

### 6. Commit and Push

```bash
cd /tmp/openclaw-patch
git add -A
git commit -m "fix(cron): descriptive summary of the change

Longer explanation of the problem, root cause, and fix approach.
Include production evidence (durations, error messages) that proves the fix."

git push origin fix/descriptive-branch-name
```

### 7. Create the Pull Request

The PR body **must** include a **Real behavior proof** section. This is a hard requirement from upstream — unit tests, mocks, CI, lint, and typechecks alone do NOT satisfy it.

```bash
source ~/.openclaw/.env && export GH_TOKEN="$GITHUB_PAT"

gh pr create \
  --repo openclaw/openclaw \
  --head kip-claw:fix/descriptive-branch-name \
  --title "fix(scope): short title" \
  --body "$(cat <<'EOF'
## Problem

Description of the issue with production evidence.

## Root Cause

What causes it in the source code (reference specific files/lines).

## Fix

What the PR changes and why.

## Real behavior proof

> Required by CONTRIBUTING.md. Must show real post-patch behavior from your own setup.

**Setup:** Raspberry Pi 5 (4GB, ARM64, Debian bookworm), OpenClaw <version>, Node <version>

**BEFORE (unpatched):**
```
<paste real production output — journal logs, health output, error messages>
```

**AFTER (patched):**
```
<paste real production output showing the fix working>
```

**What was NOT tested:**
<list edge cases or platforms you didn't cover>

Acceptable proof formats: terminal output, journal logs, `openclaw health` output,
screenshots, recordings, redacted runtime logs, linked artifacts.

NOT acceptable alone: unit tests, mocks, snapshots, lint, typechecks, CI green.

## Environment

- OpenClaw version: (from `openclaw --version`)
- Platform: Raspberry Pi 5 (4GB, ARM64, Debian bookworm)
- Node: (from `node --version`)

## AI Disclosure

- [x] AI-assisted (GitHub Copilot)
- [x] Human-run real behavior proof from own setup
- [x] Understand what the code does
EOF
)"
```

### 8. Search for Related Issues/PRs

Before or after submitting, search for existing work on the same problem:

```bash
gh search prs --repo openclaw/openclaw "relevant keywords" --state open
gh search issues --repo openclaw/openclaw "relevant keywords"
```

If a related PR exists:
- Cross-reference it from your PR
- Comment on the existing PR with your production evidence
- If it has labels like `needs-real-behavior-proof`, provide the proof

```bash
gh pr comment <number> --repo openclaw/openclaw --body "Production evidence from my environment: ..."
gh issue comment <number> --repo openclaw/openclaw --body "Cross-reference: #your-pr-number"
```

### 9. After Submission

- Resolve or reply to bot review conversations (ClawSweeper, Codex) yourself — do not leave them for maintainers
- If Codex review doesn't trigger, run `codex review --base origin/main` locally and address findings
- Monitor for maintainer feedback
- Be prepared to rebase if `upstream/main` moves ahead:

```bash
cd /tmp/openclaw-patch
git fetch upstream
git rebase upstream/main
git push origin fix/branch-name --force-with-lease
```

## PR Rules (from CONTRIBUTING.md)

- **20 PR cap per author** — exceeding this triggers auto-close with `r: too-many-prs`
- **No refactor-only PRs** unless explicitly requested by a maintainer
- **No test/CI-only PRs** for known `main` failures — maintainers track those already
- **One logical change per PR** — don't bundle unrelated fixes
- **Do not edit `CHANGELOG.md`** — maintainers add changelog entries when landing
- **Do not edit `CODEOWNERS`-protected paths** unless an owner asked for the change
- **American English** in code, comments, docs, and UI strings
- Features should generally be plugins (use plugin SDK), not core changes — ask in Discord first

## Lessons Learned

1. **Always validate locally first.** Patching compiled JS and testing in production provides irrefutable evidence for the PR.
2. **Clear `/var/tmp/openclaw-compile-cache`** after any patch to compiled JS — Node caches bytecode and will ignore your edits otherwise.
3. **Real behavior proof is mandatory.** Paste actual before/after output from production. Reviewers will block PRs without it.
4. **Search for existing PRs** before submitting. Your evidence may unblock someone else's stalled PR.
5. **Make config values overridable** rather than just bumping hardcoded constants. This is more likely to be accepted upstream.
6. **Resolve bot conversations yourself.** ClawSweeper and Codex review comments are your responsibility to address or resolve.
7. **Mark AI assistance.** If using LLM tools, disclose it and confirm you understand the code.

## Notes

- The fork at `kip-claw/openclaw` should stay in sync with upstream between PRs
- Clean up working directories after PRs are merged: `rm -rf /tmp/openclaw-patch`
- The local patched runtime at `/usr/lib/node_modules/openclaw/dist/` will be overwritten on the next `npm update -g openclaw`
