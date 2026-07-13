---
name: openclaw-upstream-pr
title: Openclaw Pull Requests
description: Guides submitting pull requests to the upstream OpenClaw repository.
tag: Code
metadata: {"openclaw": {"emoji": "🦞"}}
---

# OpenClaw Upstream Pull Request

Workflow for creating and submitting pull requests to the `openclaw/openclaw` GitHub repository from the `kip-claw/openclaw` fork.

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated as `kip-claw` (verify with `gh auth status`)
- SSH key at `~/.ssh/id_ed25519` configured for GitHub
- Crabbox CLI (`crabbox`) installed with Cloudflare provider configured
- Env vars `CRABBOX_CLOUDFLARE_RUNNER_URL` and `CRABBOX_CLOUDFLARE_RUNNER_TOKEN` in `~/.openclaw/.env`

```bash
# gh is already authenticated system-wide — no need to export GH_TOKEN.
# Source the env only for Crabbox credentials:
source ~/.openclaw/.env && export CRABBOX_CLOUDFLARE_RUNNER_URL CRABBOX_CLOUDFLARE_RUNNER_TOKEN
```

**CRITICAL env note:** values in `~/.openclaw/.env` are not auto-loaded into random interactive shells. Before any Crabbox command in a fresh terminal/session, run the `source ~/.openclaw/.env` line above (or explicitly pass `CRABBOX_CLOUDFLARE_RUNNER_URL`/`CRABBOX_CLOUDFLARE_RUNNER_TOKEN`). If you skip this, Crabbox may appear "not configured" even though the values exist in the file.

**Prefer `gh` over naked `git`/curl wherever an equivalent exists.** `gh` handles auth, fork-awareness, and API plumbing for you. Only fall back to raw `git` for operations `gh` doesn't cover (commit, push, rebase, local branching).

## Fork Setup

The fork lives at `kip-claw/openclaw`. Use `gh repo clone` — it automatically sets the `upstream` remote to the parent repo for forks:

```bash
gh repo clone kip-claw/openclaw /tmp/openclaw-patch
cd /tmp/openclaw-patch
# `upstream` remote is already configured by `gh repo clone` for forks. Verify:
git remote -v   # should show origin=kip-claw/openclaw, upstream=openclaw/openclaw

# Sync the fork's default branch with upstream before branching:
gh repo sync kip-claw/openclaw --source openclaw/openclaw
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

## Extension / Plugin PRs

Not every PR is a core `src/` fix. Bundled plugins live under `extensions/<name>/` (e.g. `memory-wiki`, `memory-core`, channel plugins). The maintainers' stated default is **"most features should be third-party plugins, not core changes."** A change to a bundled extension is more defensible than a core change, but still expect pushback — if the PR adds a capability, preempt it in the body with a short **"Why in core / why this extension owns it"** paragraph (e.g. it's a thin read-only accessor over data the plugin already derives internally; a third-party plugin couldn't reach it without the `unsafe-local` escape hatch or duplicating logic).

**Plugin manifest contract (bites silently).** Every agent tool a plugin registers via `api.registerTool` **must** also be declared in that plugin's `extensions/<name>/openclaw.plugin.json` under `contracts.tools` (sorted array of tool names). If you add a tool in `index.ts`/`src/tool.ts` but forget the manifest, the plugin registry **rejects the registration at runtime** (`plugin must declare contracts.tools for: <name>`) and the `test:contracts:plugins` lane fails — but `test:extension <name>` does **not** catch it. This is exactly the kind of thing `codex review` flags and the per-extension test misses.

**Validation commands for extension PRs** (run remotely on Crabbox — see git caveat in Step 5):

```bash
pnpm build
pnpm tsgo:extensions          # typecheck extension source
pnpm tsgo:extensions:test     # typecheck extension tests
pnpm lint:extensions          # oxlint (0 warnings / 0 errors expected)
oxfmt --check extensions/<name>   # formatter (NOT prettier — repo uses oxfmt)
pnpm test:extension <name>    # that plugin's vitest suite
pnpm test:contracts:plugins   # cross-plugin contract lane (enforces the manifest above)
pnpm format:docs:check        # if the PR touches docs/
```

Repo tooling is **oxfmt** (`.oxfmtrc.jsonc`) + **oxlint**, **tsgo** for typecheck, **vitest** for tests, `format-docs.mjs` + markdownlint-cli2 for docs. There is **no prettier** — `pnpm exec prettier` will "not found". `oxfmt <file>` auto-fixes; `oxfmt --check` verifies.

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

**Remote-first test policy (default):** run every test/validation that can run remotely on Crabbox, not on the Pi. Use local Pi execution only when the check requires local runtime state, credentials, or live channel integrations that cannot exist in an ephemeral Crabbox container.

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
| `crabbox run --provider cloudflare --shell 'pnpm docs:list'` | docs index validation | Docs-only or doc-touching PRs |
| `crabbox job run proof` | build + run proof commands | Generate behavior proof for PR body |
| `crabbox job run gateway-smoke` | build + start gateway + health check | Proving gateway boots with patches applied |
| `crabbox job run check` | build + full check (incl. lint) | Final validation (may hit timeout on large repos) |
| `crabbox job run test-changed` | targeted tests | Validating specific changes |

#### Iterative development (warm box)

For rapid feedback while developing a fix. The huge win is **not re-paying `pnpm install` + `pnpm build` (~8 min combined) on every run** — pay it once, then iterate in seconds.

> [!CRITICAL] **Warm boxes have NO `.git` — git-dependent tests fail unless you init it.**
> Ephemeral `crabbox run` (no `--id`) does `git init/commit` for you. **The warm-box path (`crabbox warmup` + `crabbox run --id`) syncs via rsync and does NOT include `.git`** — the workspace is not a git repo. Many contract tests enumerate files via `git ls-files` (their names read `"lists … from git without walking …"`). With no git they fall back to `fs.readdirSync` and fail en masse with `expected "readdirSync" to not be called at all, but actually been called N times`. In this session **8 of the `test:contracts:plugins` files** failed this way — a pure environment artifact, nothing to do with the code. **Always `git init && git add -A && git commit` in the warm-box workspace before running `test:contracts:plugins` (or any git-listing test).** With git present the suite passed 986/986; without it, 8 spurious failures.

```bash
# Lease a persistent container — leases in ~1s ("warmup complete total=854ms")
crabbox warmup --provider cloudflare
# Returns an id (cbx_...) + slug (e.g. "brisk-crab"). Reuse the cbx_ id for all runs.

# --reclaim is REQUIRED if you run from a different cwd than where you warmed up
# (else: "lease cbx_... is claimed by repo <path>; use --reclaim").
# First run: set up git (MANDATORY, see callout) + deps
crabbox run --id cbx_... --reclaim --provider cloudflare -- bash -lc \
  'git init -q && git config user.email t@t.co && git config user.name t && git add -A && git commit -q -m snapshot && pnpm install --frozen-lockfile'

# Subsequent runs: build/test (git + deps persist on the box)
crabbox run --id cbx_... --reclaim --provider cloudflare -- bash -lc 'pnpm build && pnpm tsgo:extensions'
crabbox run --id cbx_... --reclaim --provider cloudflare -- bash -lc 'pnpm test:contracts:plugins 2>&1 | tail -40'

# Done — release. NOTE: `stop` takes the id POSITIONALLY, provider flag FIRST.
# `crabbox stop --id <x>` is WRONG (`flag provided but not defined: -id`).
crabbox stop --provider cloudflare cbx_...
# If you forget, it auto-releases after the 30m idle timeout — no 24/7 box needed.
```

**Sizing / limits (asked-and-answered):** default `-type standard-4`, `-class beast` are already the top tier. The ~15 min cutoff is a **Cloudflare Worker wall-clock/stream limit**, not CPU starvation — a bigger `-type` finishes faster (buying headroom) but does **not** raise the ceiling. `-idle-timeout` (default 30m) governs auto-release; the box is never idle mid-run so that's not what cuts long commands. For cross-session speed without a live box, see `crabbox checkpoint` (snapshot post-install/build) and `crabbox cache warm`.

**`set -e` masks test failures.** In a crabbox script, `set -e` + `pnpm test ...; echo EXIT=$?` aborts the whole script the instant the test returns non-zero — *before* your echo/log-dump runs, so you never see why it failed. Either drop `set -e` around the test, or write output to a file and always `cat`/`tail` it regardless of exit: `pnpm test:contracts:plugins > /tmp/c.log 2>&1; echo "EXIT=$?"; tail -60 /tmp/c.log`.

**Flaky streaming — retry, don't panic.** Transient `cloudflare stream ended before completion` and HTTP2 `PROTOCOL_ERROR` on upload happen; they are not real failures. Retry. To minimize exposure, **split work into short commands** (install / build / each test suite / proof) rather than one long chained run that risks the wall-clock and a mid-stream drop.

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

#### Proof via a throwaway vitest spec (best for plugin/tool PRs — no build needed)

Importing a tool from `dist/` for proof forces a full `pnpm build` (~slow, and the step most likely to hit the stream limit / a mid-stream drop). Avoid it: **write a throwaway `*.test.ts` that invokes the real tool/function against a seeded fixture and `console.log`s the output, then run it with vitest** — vitest transforms TS on the fly, so no build is required and it runs in seconds on a warm box.

```ts
// extensions/<name>/src/_proof.test.ts  — TEMP, do NOT commit
import { it } from "vitest";
import { createWikiOpenItemsTool } from "./tool.js";
import { resolveMemoryWikiConfig } from "./config.js";
// ...seed a temp vault on disk...
it("PROOF", async () => {
  const tool = createWikiOpenItemsTool(config);
  const out = await tool.execute("proof", {});
  console.log(out.content[0].text);
  console.log("details =", JSON.stringify(out.details));
});
```

```bash
crabbox run --id cbx_... --reclaim --provider cloudflare -- bash -lc \
  'pnpm exec vitest run extensions/<name>/src/_proof.test.ts 2>&1 | tail -60'
```

Create the spec **locally** (so it syncs to the box), capture the printed output for the PR, then delete it before committing (`rm extensions/<name>/src/_proof.test.ts`) — it must not land in the PR. vitest prints `console.log` under a `stdout | …` header.

#### When to use Pi instead of Crabbox

Use local Pi production evidence when the proof requires:
- A running gateway with real plugins/channels connected
- Active cron jobs with historical state
- Real message delivery (Telegram, Matrix, etc.)
- Network-dependent features (health checks against live services)
- **Auth/credential resolution** — stored OAuth tokens, API keys in the profile store, or cross-provider credential lookups (Crabbox containers have no stored credentials)

For these cases, follow Step 3's local validation approach and paste journal logs.

**Lesson learned:** Crabbox is excellent as a remote CI (build + typecheck confirmation without local toolchain), but for fixes involving credential resolution (e.g. openai/openai-codex cross-provider auth), the proof MUST come from the Pi where real credentials exist. A fresh container cannot exercise auth paths that depend on stored OAuth tokens. Plan accordingly — use `quick-check` for build validation, then patch the local Pi runtime (`/usr/lib/node_modules/openclaw/dist/`) for behavior proof. Remember the dist files use **tabs** for indentation; Python `sed`/replace scripts must account for this.

### 7. Commit and Push

`git` is still the right tool for local commits and pushing branches (no `gh` equivalent for these):

```bash
cd /tmp/openclaw-patch
git add -A
git commit -m "fix(cron): descriptive summary of the change

Longer explanation of the problem, root cause, and fix approach.
Include production evidence (durations, error messages) that proves the fix."

git push -u origin fix/descriptive-branch-name
```

### 8. Create the Pull Request

The PR body **must** include a **Real behavior proof** section. This is a hard requirement from upstream — unit tests, mocks, CI, lint, and typechecks alone do NOT satisfy it.

> [!WARNING] **The external-PR gate is a LITERAL heading match, not a content check.**
> The `Real behavior proof` CI job runs `scripts/github/real-behavior-proof-check.mjs` → `real-behavior-proof-policy.mjs`, which requires the body to contain headings matching the **exact** regexes `/^#{2,6}\s+What Problem This Solves\b/im` **and** `/^#{2,6}\s+Evidence\b/im`. A semantically-identical but reworded heading (e.g. `## What problem does this solve?`) **fails the job** even with perfect content. Use the verbatim headings **`## What Problem This Solves`** and **`## Evidence`**. The section must also be non-empty / not a placeholder (`n/a`, `tbd`, `-`, etc. count as missing). Maintainer/collaborator/bot PRs skip this gate; external PRs (like ours) do not.

> [!NOTE] **Editing the PR body/title: use `gh api`, not `gh pr edit`.**
> `gh pr edit` resolves the author's org membership and fails on this token: `GraphQL: … 'login' field requires … 'read:org' … token has only … [repo, workflow, …]`. Update the body via the REST API instead (no org scope needed):
> ```bash
> gh api -X PATCH repos/openclaw/openclaw/pulls/<N> -f body="$(cat body.md)"
> ```
> Fetch the current body first (`gh api repos/openclaw/openclaw/pulls/<N> --jq .body`) if you're appending rather than replacing.

```bash
# gh is system-authenticated — no env export needed.
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

- [x] AI-assisted (Claude Code / Claude Opus 4.8)
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

Use `gh` to monitor the PR after creation — no need to leave the terminal:

```bash
gh pr view --repo openclaw/openclaw <number>          # full PR detail + comments
gh pr checks --repo openclaw/openclaw <number>        # CI status
gh pr status --repo openclaw/openclaw                 # all your PRs at a glance
gh pr diff --repo openclaw/openclaw <number>          # confirm what reviewers see
```

- Resolve or reply to bot review conversations (ClawSweeper, Codex) yourself — do not leave them for maintainers (`gh pr comment` / `gh pr review` for replies)
- If Codex review doesn't trigger, run `codex review --base origin/main` locally and address findings
- Monitor for maintainer feedback

#### ClawSweeper — the automated reviewer (take it seriously)

`clawsweeper[bot]` is the primary automated review on every PR. It posts **one durable, marker-backed comment** per PR and **edits that same comment** on each re-review (no duplicate comments). Key behaviors observed:

- **Its findings are high quality.** In this session it correctly caught a runtime-breaking manifest omission (P1) that all local checks missed, then on the next round found 3 more real defects (an opaque-id-instead-of-text bug, an `anyOf`-vs-flat-enum provider-compat issue, and filtered-vs-unfiltered count inconsistency) plus called out that a hand-written "proof" didn't match actual code behavior. **Verify each finding against the code, but assume it's right until proven otherwise** — don't argue, fix.
- **It gates on real proof.** Status `📣 needs proof` / rating `🦪 silver shellfish` etc.; it explicitly blocks when the posted proof "does not demonstrate the registered tool through OpenClaw." A fabricated/idealized proof block will be caught and called out. Generate proof from an actual invocation (see the vitest-spec technique above).
- **Re-trigger with `@clawsweeper re-review`** (PR author or write-access can request review-only). Post it as a normal issue comment:
  ```bash
  gh api repos/openclaw/openclaw/issues/<N>/comments -f body="@clawsweeper re-review"
  ```
  `re-review`/`re-run` do **not** start autofix/automerge — those are maintainer-only (`@clawsweeper autofix|automerge|address review`).
- **Respond point-by-point in a new comment**, don't silently push. Reference each finding, say what changed, and paste the real proof. It (and maintainers) read that thread.

#### Codex CLI review (pre-flight, before you even push)

Run `codex review --base origin/main` locally to catch what CI's ClawSweeper will catch — cheaper to fix before submitting. Model gotchas on the ChatGPT-account auth: **`gpt-5.5` works**; `gpt-5.3-codex` (not on the account) and `gpt-5.6-terra` (needs a newer CLI) are rejected. Override with `-c model="gpt-5.5"`. If auth expires (`refresh token already used` / `token_expired`), re-login from the Pi terminal. Note this also doubles as an early-warning signal for the terra OAuth expiry the deployment tracks.
- Be prepared to rebase if `upstream/main` moves ahead. Use `gh repo sync` to update the fork's default branch first, then rebase locally (rebase has no `gh` equivalent):

```bash
cd /tmp/openclaw-patch
gh repo sync kip-claw/openclaw --source openclaw/openclaw
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
13. **Prefer `gh` over naked `git`/curl.** `gh` is system-authenticated and fork-aware: `gh repo clone` sets `upstream` automatically, `gh repo sync` updates the fork without manual fetch/merge, `gh pr {create,view,checks,diff,comment,status}` cover the PR lifecycle. Only fall back to raw `git` for local-only operations: commit, push, rebase, branch. **Exception:** editing a PR body/title needs `gh api -X PATCH …/pulls/<N> -f body=…` because `gh pr edit` demands a `read:org` scope this token lacks.
14. **Warm boxes have no `.git`.** The single biggest time-sink this session: `test:contracts:plugins` failed 8 files on a warm box purely because rsync doesn't sync `.git`, so git-listing tests fell back to `readdirSync`. Always `git init && git add -A && git commit` in the warm-box workspace before git-dependent tests. Ephemeral `crabbox run` (no `--id`) doesn't hit this. Don't waste time blaming your diff — check `git rev-parse --is-inside-work-tree` in the box first.
15. **The external-PR CI gate matches heading text literally.** Body must contain verbatim `## What Problem This Solves` and `## Evidence`. Reworded headings fail even with correct content (`real-behavior-proof-policy.mjs`).
16. **ClawSweeper is right more than you'd think — fix, don't argue.** It caught a manifest omission and 3 correctness defects local checks missed. Verify against code, then fix. Re-trigger with an `@clawsweeper re-review` issue comment; respond point-by-point in a new comment with real proof.
17. **Never fabricate proof.** An idealized/hand-written "real behavior proof" that the code can't actually produce will be caught (by ClawSweeper, and it's just wrong). Generate proof from a real invocation — for tools/plugins, a throwaway `*.test.ts` run via `pnpm exec vitest run` (no build needed) is the fast, reliable path.
18. **Plugin tools must be in `openclaw.plugin.json` `contracts.tools`.** Register a tool in code but omit the manifest → runtime rejection + `test:contracts:plugins` failure, invisible to `test:extension <name>`.
19. **`set -e` in crabbox scripts hides the failing test log.** It aborts before your echo/`cat` runs. Dump the log unconditionally and inspect it.
20. **Beware stray NUL bytes turning a file "binary."** A literal `\x00` (e.g. an intended separator that came through as NUL) makes git treat the source as binary — `git diff --numstat` shows `-  -`, `git diff` says "Binary files differ", `file` reports `data`, and the PR diff won't render. Detect with `python3 -c "d=open(p,'rb').read(); print([i for i,b in enumerate(d) if b==0])"`; fix by replacing the byte. Sanity-check `git diff --stat` doesn't show `Bin` for a text file before committing.
21. **Split crabbox work into short commands.** Install / build / each test suite / proof as separate runs beats one long chain — dodges the ~15 min Worker wall-clock and transient stream drops (`stream ended before completion`, HTTP2 `PROTOCOL_ERROR`), which are just retryable flakes.
22. **`crabbox stop` syntax:** `crabbox stop --provider cloudflare <cbx_id>` (provider flag first, id positional). `--id` is not a valid `stop` flag. Warm boxes also auto-release after the 30m idle timeout, so 24/7 leasing is never required.

## Notes

- The fork at `kip-claw/openclaw` should stay in sync with upstream between PRs
- Clean up working directories after PRs are merged: `rm -rf /tmp/openclaw-patch`
- The local patched runtime at `/usr/lib/node_modules/openclaw/dist/` will be overwritten on the next `npm update -g openclaw`
