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
- Crabbox CLI (`crabbox`) installed with Cloudflare provider configured
- Env vars `CRABBOX_CLOUDFLARE_RUNNER_URL` and `CRABBOX_CLOUDFLARE_RUNNER_TOKEN` in `~/.openclaw/.env`

```bash
source ~/.openclaw/.env && export GH_TOKEN="$GITHUB_PAT" CRABBOX_CLOUDFLARE_RUNNER_URL CRABBOX_CLOUDFLARE_RUNNER_TOKEN
```

## Fork Setup

The fork lives at `kip-claw/openclaw`. Clone it to a temporary working directory:

```bash
git clone --depth 1 git@github.com:kip-claw/openclaw.git /tmp/openclaw-patch
cd /tmp/openclaw-patch
git remote add upstream git@github.com:openclaw/openclaw.git
git fetch upstream
git checkout -b fix/descriptive-branch-name upstream/main
```

The repo includes a `.crabbox.yaml` that configures Cloudflare remote builds (provider, instance class, setup steps, named jobs). No local `pnpm install` is needed — dependencies install on the remote container.

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

### 5. Build & Test via Crabbox (Cloudflare)

Crabbox runs build and typecheck remotely on Cloudflare containers (standard-4: 4 vCPU, 12 GiB RAM). This satisfies the CONTRIBUTING.md requirement to "Run tests: `pnpm build && pnpm check`" before submitting. The `.crabbox.yaml` in the repo handles provider selection, dependency installation, and named jobs.

**Important:** Crabbox can handle both build validation AND behavior proof generation. The `quick-check` job proves compilation + typecheck. The `proof` job builds the patched binary and runs targeted commands to produce real output for the PR body. For fixes that require runtime state (gateway running, cron jobs active), use local Pi production evidence instead.

#### Quick one-shot (build + typecheck)

```bash
cd /tmp/openclaw-patch
crabbox job run quick-check
```

This syncs your working tree to a fresh container, runs git init + pnpm install + `pnpm build` + typecheck. Completes in ~3-4 minutes.

#### Named jobs (from .crabbox.yaml)

| Job | What it does | Use when |
|-----|--------------|----------|
| `crabbox job run quick-check` | build + typecheck | Before committing (fast, reliable) |
| `crabbox job run build` | build only | Verify compilation |
| `crabbox job run proof` | build + run proof commands | Generate behavior proof for PR body |
| `crabbox job run gateway-smoke` | build + start gateway + health check | Proving gateway boots with patches applied |
| `crabbox job run check` | build + full check (incl. lint) | Final validation (may hit timeout on large repos) |
| `crabbox job run test-changed` | targeted tests | Validating specific changes |

#### Iterative development (warm box)

For rapid feedback while developing a fix:

```bash
# Lease a persistent container
crabbox warmup --provider cloudflare
# Returns a slug like "brisk-crab" — reuse it for all subsequent commands

# First run: set up git + deps
crabbox run --id brisk-crab -- 'git config --global user.email x@x && git config --global user.name x && git init -q && git add -A && git commit -m x -q && corepack enable && pnpm install --frozen-lockfile'

# Subsequent runs: just build/typecheck (git + deps persist)
crabbox run --id brisk-crab -- 'git add -A && git commit -m x -q --allow-empty && pnpm build && pnpm tsgo:core && pnpm tsgo:extensions'

# Done — release the container
crabbox stop brisk-crab
```

#### Troubleshooting

```bash
# Verify provider is healthy
crabbox doctor --provider cloudflare

# If a container hits stream timeout, use quick-check instead of full check
# Cloudflare containers have ~15 min stream limit — lint can exceed this on large repos
```

**Limitations:**
- ~15 min stream timeout — full lint (`pnpm check`) may exceed this; use `quick-check` for reliable runs
- 20 GB disk — fits the monorepo comfortably
- No SSH into the container — output streaming only
- Containers are ephemeral; warm boxes persist only while leased
- Full test suite (`pnpm test`) exceeds the timeout; use `test-changed` or run tests in upstream CI

### 6. Generate Behavior Proof via Crabbox

After `quick-check` passes, generate real behavior proof for the PR body. The `proof` job in `.crabbox.yaml` builds the patched binary and runs commands that demonstrate the fix works.

#### Customize the proof job

Edit `.crabbox.yaml`'s `proof` job — replace the placeholder proof commands with fix-specific ones:

```yaml
  proof:
    command: >-
      git config --global user.email x@x &&
      git config --global user.name x &&
      git init -q && git add -A && git commit -m x -q &&
      corepack enable &&
      pnpm install --frozen-lockfile &&
      pnpm build &&
      echo "=== PROOF START ===" &&
      node openclaw.mjs --version &&
      echo "--- fix-specific proof below ---" &&
      node openclaw.mjs <your-proof-command> &&
      echo "=== PROOF END ==="
```

**What to put in proof commands (depends on fix type):**

| Fix type | Proof command examples |
|----------|----------------------|
| CLI behavior | `node openclaw.mjs <subcommand> --flag` |
| Config resolution | `node -e "import('./dist/entry.js').then(...)"`  |
| Cron/watchdog | `node openclaw.mjs cron list 2>&1 \| head -20` |
| Build artifact | `ls -la dist/<expected-file>` |
| Error handling | `node openclaw.mjs <trigger-condition> 2>&1` (show graceful handling) |

#### Run proof

```bash
cd /tmp/openclaw-patch
crabbox job run proof
```

Completes in ~3 min. Copy the output between `=== PROOF START ===` and `=== PROOF END ===` into the PR body's **Real behavior proof** section.

#### Warm box variant (for iterating on proof commands)

```bash
crabbox warmup --provider cloudflare
# First: setup + build
crabbox run --id <slug> -- 'git config --global user.email x@x && git config --global user.name x && git init -q && git add -A && git commit -m x -q && corepack enable && pnpm install --frozen-lockfile && pnpm build'
# Then iterate on proof commands quickly (no rebuild needed):
crabbox run --id <slug> -- 'node openclaw.mjs <proof-command>'
crabbox run --id <slug> -- 'node openclaw.mjs <another-proof-command>'
# Done
crabbox stop <slug>
```

#### When to use Pi instead of Crabbox

Use local Pi production evidence when the proof requires:
- A running gateway with real plugins/channels connected
- Active cron jobs with historical state
- Real message delivery (Telegram, Matrix, etc.)
- Network-dependent features (health checks against live services)

For these cases, follow Step 3's local validation approach and paste journal logs.

### 7. Commit and Push

```bash
cd /tmp/openclaw-patch
git add -A
git commit -m "fix(cron): descriptive summary of the change

Longer explanation of the problem, root cause, and fix approach.
Include production evidence (durations, error messages) that proves the fix."

git push origin fix/descriptive-branch-name
```

### 8. Create the Pull Request

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

**Setup:** Cloudflare Container (standard-4: 4 vCPU, 12 GiB RAM, Node 24.x) via Crabbox
*(or: Raspberry Pi 5 (4GB, ARM64, Debian bookworm) if proof requires running gateway)*

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

### 9. Search for Related Issues/PRs

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

### 10. After Submission

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
8. **Use warm boxes for iteration.** Leasing a warm container avoids repeated pnpm installs (~23s each). Stop it when done to free resources.
9. **Don't install deps locally.** The Pi has limited disk; let Crabbox handle pnpm install on the remote container.
10. **Crabbox handles both build proof AND behavior proof.** The `proof` job builds the binary and runs targeted commands to generate real output. Only fall back to local Pi when proof requires a running gateway, real channels, or active cron state.
11. **Use `quick-check` over `check`.** Full lint can exceed Cloudflare's ~15 min stream timeout. `quick-check` (build + typecheck) is reliable and catches most issues.
12. **Base64-encode complex shell scripts in `.crabbox.yaml`.** Crabbox wraps commands in temp script files, breaking embedded quotes. For scripts with loops, conditionals, or single/double quotes, base64-encode the script and decode on the container: `echo <base64> | base64 -d > /tmp/script.sh && chmod +x /tmp/script.sh && /tmp/script.sh`. The `gateway-smoke` job uses this pattern.

## Notes

- The fork at `kip-claw/openclaw` should stay in sync with upstream between PRs
- Clean up working directories after PRs are merged: `rm -rf /tmp/openclaw-patch`
- The local patched runtime at `/usr/lib/node_modules/openclaw/dist/` will be overwritten on the next `npm update -g openclaw`
