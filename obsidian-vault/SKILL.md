---
name: obsidian-vault
description: Reads, writes, edits, and searches notes in Ben's Obsidian vault.
tag: Work
---

# Obsidian Knowledge Base

Vault path: `{{HOME}}/obsidian-vault`

Use `read`, `write`, `edit`, and `exec` directly.

## Working rules

- Always work inside `{{HOME}}/obsidian-vault`, never in the workspace
- **Never read, edit, create, or delete anything under `Wiki/Kip/`** — that folder is managed by the `memory-wiki` plugin
- Read a note before editing it
- Prefer `rg` for search, then `read` the matching files
- Use the existing category structure: Work, Teaching, Home, Open Source
- Keep filenames descriptive, because the filename is the note title
- Do not delete notes unless Ben explicitly asks for deletion
- Use wikilinks like `[[Note Name]]` when adding references inside notes

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

```bash
rg -il "search terms" {{HOME}}/obsidian-vault/ --glob '*.md'
```

List notes only when needed:

```bash
find {{HOME}}/obsidian-vault -name '*.md' -not -path '*/.*'
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
1. Read the file first
2. Make the smallest sensible edit
3. Update `modified` if frontmatter exists
4. Do not add frontmatter to older notes unless Ben asks or you are creating the note

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
- Between the active sections and `## Done` there is a `## Since Last Digest` buffer. It holds checked items that have not yet been swept into the monthly archive. The `todo-archival` skill moves items from `## Done` into this buffer; the `news-apps-digest` skill flushes the buffer into `Archive/Done-Items.md` after Ben confirms a digest has been sent. Do not delete or reorder items in `## Since Last Digest` during routine cleanup.
- Ensure each todo item has a relevant hashtag when possible. Use only canonical tags from `{{HOME}}/.openclaw/workspace/skills/news-apps-digest/taxonomy.yaml` (run the `kip-todo-lint` skill to validate or auto-rename aliases).
- Remove obvious typos and stray empty lines during routine cleanup.

When Ben names today's priorities:
1. Move those items into `### High Priority`
2. Put the most urgent ones first
3. Treat high priority as current focus, not permanent importance

When Ben says something is done or asks to check it off:
1. Mark the checkbox as complete
2. Move the item to the bottom `## Done` section
3. Ensure no blank lines remain after moving items
4. Do not leave checked items in active sections

Do not move items into `## Since Last Digest` or write to `Archive/Done-Items.md` from this skill. Sweeping `## Done` into the buffer is the `todo-archival` skill's job; flushing the buffer to the monthly archive is `news-apps-digest`'s job.

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

- Daily: Correct typos, clean up misformatted notes, ensure relevant (canonical) hashtags, remove empty lines, and move completed items to the bottom `## Done` section in `Todo.md`. Run `kip-todo-lint` if any new or suspect tags appear.
- Weekly: Run the `todo-archival` skill to move `## Done` items into `## Since Last Digest`. Do not flush the buffer to `Archive/Done-Items.md` here — that happens automatically when Ben sends a digest via `news-apps-digest`.
- Monthly: review `Ideas.md` and category notes in `Documents/`
- Quarterly: archive stale notes and simplify the vault structure where needed
