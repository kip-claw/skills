---
name: "obsidian-vault"
description: "Deterministic Obsidian vault edits without approval-prone shell/Python by default."
tag: Work
---

# Obsidian Knowledge Base

Vault path: `{{HOME}}/obsidian-vault`

Use OpenClaw native file tools first: `read`, `edit`, `write`, and `apply_patch`.

Use shell commands only when the task genuinely requires command output that native tools cannot provide. Never use shell heredocs or inline Python for routine vault edits.

## Approval-safe operating rule

Routine note and Todo work must not require Telegram approval prompts.

Preferred order:

1. `read` the relevant absolute file path.
2. Make deterministic exact-text changes with `edit`.
3. Use `write` only when creating a new note or replacing a fully inspected/generated file.
4. Use `apply_patch` only when multiple vault files need coordinated deterministic changes.
5. Use `exec` only as a last resort for searches, lint checks, or git/status operations; avoid it for content mutation unless Ben explicitly asks or the native tools cannot do the job.

Important: `/usr/bin/obsidian` is not a usable Obsidian.md vault CLI on this host. It is the npm package `obsidian-cli` v0.5.1 for ObsidianQA test-run imports into Obsidianqa.com, requiring API credentials. Do not use it for unattended Markdown vault edits or note maintenance.

Do not run:

- `python - <<'PY'`, `python3 - <<'PY'`, `cat <<EOF`, `tee <<EOF`, or any other shell heredoc.
- Inline Python/Node/Ruby/Perl one-liners to edit markdown when `edit` or `write` can do it.
- Broad `find`/`ls` discovery for normal note updates.

If `exec` approval is triggered, stop and switch to native file tools when possible instead of retrying variations of the same command.

## Working rules

- Always work inside `{{HOME}}/obsidian-vault`, never in the workspace.
- **Never read, edit, create, or delete anything under `Wiki/Kip/`** — that folder is managed by the `memory-wiki` plugin.
- Read a note before editing it.
- Prefer known absolute paths for root files such as `{{HOME}}/obsidian-vault/Todo.md` and `{{HOME}}/obsidian-vault/Ideas.md`.
- For targeted search, prefer native `read` of likely files first. Use `exec` + `rg` only when the target file is genuinely unknown.
- Use the existing category structure: Work, Teaching, Home, Open Source.
- Keep filenames descriptive, because the filename is the note title.
- Do not delete notes unless Ben explicitly asks for deletion.
- Use wikilinks like `[[Note Name]]` when adding references inside notes.

## Folder map

```text
{{HOME}}/obsidian-vault/
├── Archive/
├── Documents/
│   ├── Work/
│   ├── Teaching/
│   ├── Home/
│   └── Open Source/
├── Wiki/
│   └── Kip/          ← OFF LIMITS (memory-wiki plugin)
├── Ideas.md
├── Todo.md
└── README.md
```

## Search

Use targeted search instead of browsing the whole vault.

Approval-safe approach:

1. If the request names Todo, Ideas, or a likely note path, read that file directly.
2. If the path is unknown but the note title is clear, infer the likely path under `Documents/<category>/` and read it.
3. Only then use `exec` with `rg` for search.

When shell search is necessary, keep it read-only and narrow:

```bash
rg -il "search terms" {{HOME}}/obsidian-vault/ --glob '*.md' --glob '!Wiki/Kip/**'
```

List notes only when needed, and exclude `Wiki/Kip/`:

```bash
find {{HOME}}/obsidian-vault -name '*.md' -not -path '*/.*' -not -path '{{HOME}}/obsidian-vault/Wiki/Kip/*'
```

## Create or edit notes

When creating a new note, use an absolute path under the vault.

Use this frontmatter template when creating notes:

```markdown
---
created: '<ISO timestamp>'
modified: '<ISO timestamp>'
---

# Title
```

When editing a note:

1. Read the file first.
2. Make the smallest sensible deterministic edit.
3. Prefer `edit` with exact old/new text. If multiple nearby changes are needed, merge them into one replacement.
4. Update `modified` if frontmatter exists.
5. Do not add frontmatter to older notes unless Ben asks or you are creating the note.
6. Verify by reading the changed lines back. Use git status/commit only when explicitly requested or already part of the workflow.

## Todo rules

`Todo.md` is the root task list.

Life-area sections:

- `## Work`
- `## Home`
- `## Open Source`
- `## Teaching`

Inside `## Work`, keep:

- `### High Priority` for today's focus
- `### Medium Priority` for active but secondary work

Global Todo convention:

- Keep a single `## Done` section at the bottom of `Todo.md` for all completed items across Work, Home, Open Source, and Teaching.
- Do not use a `## Since Last Digest` section. The old buffer workflow is deprecated.
- Completed items stay in `## Done` until Ben confirms a News Apps digest has been sent or explicitly asks to archive/sweep them. Then the digest workflow moves them into `Archive/Done-Items.md` with a `<!-- digest: YYYY-MM-DD -->` marker and clears `## Done` fully.
- Ensure each todo item has a relevant hashtag when possible. Use only canonical tags from `{{HOME}}/.openclaw/workspace/skills/news-apps-digest/taxonomy.yaml`.
- Run the `kip-todo-lint` skill for hashtag validation when tags are new or suspect. Do not use ad hoc Python cleanup for tag fixes.
- Remove obvious typos and stray empty lines during routine cleanup, but do it with exact `edit` replacements after reading `Todo.md`.

When Ben names today's priorities:

1. Read `{{HOME}}/obsidian-vault/Todo.md`.
2. Move those items into `### High Priority` using exact `edit` replacements.
3. Put the most urgent ones first.
4. Treat high priority as current focus, not permanent importance.
5. Read the affected section back to verify.

When Ben says something is done or asks to check it off:

1. Read `{{HOME}}/obsidian-vault/Todo.md`.
2. Mark the checkbox as complete.
3. Move the item to the bottom `## Done` section.
4. Ensure no blank lines remain after moving items.
5. Verify by reading the affected active section and `## Done`.
6. Do not leave checked items in active sections.

Do not write to `Archive/Done-Items.md` from this skill unless Ben explicitly asks to archive/sweep completed items after a digest.

When work is no longer urgent, move it back to `### Medium Priority`.

## Ideas rules

`Ideas.md` is the single root list for future work.

- Keep ideas under the matching category heading.
- Keep idea entries short and scannable.
- If an idea becomes active, move it into `Todo.md`.

## Documents rules

`Documents/` holds longer-lived notes.

- Use `Documents/Work/` for work notes.
- Use `Documents/Teaching/` for teaching notes.
- Use `Documents/Home/` for home notes.
- Use `Documents/Open Source/` for open source notes.
- Keep subfolders when they are already useful, like `Documents/Teaching/CUNY/`.
- Put reference notes, planning notes, and support material in `Documents/`, not in `Todo.md` or `Ideas.md`.

## Periodic review cues

- Daily: Correct typos, clean up misformatted notes, ensure relevant canonical hashtags, remove empty lines, and move completed items to the bottom `## Done` section in `Todo.md` using native file tools. Run `kip-todo-lint` if any new or suspect tags appear.
- After Ben says a News Apps digest has been sent, sweep `## Done` into `Archive/Done-Items.md` with that digest date marker, then leave `## Done` empty.
- Monthly: review `Ideas.md` and category notes in `Documents/`.
- Quarterly: archive stale notes and simplify the vault structure where needed.

## Failure handling

If a vault operation triggers an approval prompt unexpectedly:

1. Do not retry the same task with another shell/Python variation.
2. Explain briefly that the shell path hit approval.
3. Switch to `read`/`edit`/`write` if possible.
4. Ask Ben only if native tools cannot complete the task safely.
