---
name: obsidian-vault
description: Works with the Obsidian vault knowledge base to read, create, edit, and search notes.
---

# Obsidian Knowledge Base

Vault path: `{{HOME}}/obsidian-vault`

Use `read`, `write`, `edit`, and `exec` directly. There is no `obsidian_*` tool.

## Working rules

- Always work inside `{{HOME}}/obsidian-vault`, never in the workspace
- Read a note before editing it
- Prefer `rg` for search, then `read` the matching files
- Ask Ben which folder to use when the destination is not obvious
- Keep filenames descriptive, because the filename is the note title
- Do not delete notes, archive or move them instead
- Use wikilinks like `[[Note Name]]` when adding references inside notes

## Folder map

```text
{{HOME}}/obsidian-vault/
├── Archive/
├── Ideas/
├── Projects/
├── Todo.md
├── Projects.md
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
- Ensure each todo item has a relevant hashtag when possible.
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

Do not perform monthly archive movement to `Archive/Done-Items.md` in this skill. For archival runs, use the `todo-archival` skill.

When work is no longer urgent, move it back to `### Medium Priority`.

## Project rules

Projects live in two places:
- `Projects.md` for the dashboard view
- `Projects/` for detail files

When creating a project:
1. Create `Projects/Project Name.md`
2. Include `status`, `created`, and `modified` in frontmatter
3. Add a link in `Projects.md`

When updating a project:
1. Edit the detail file
2. Update `modified`
3. If status changes, update both the detail file frontmatter and the entry in `Projects.md`

Allowed status values:
- `active`
- `paused`
- `complete`

## Periodic review cues

- Daily: Correct typos, clean up misformatted notes, ensure relevant hashtags, remove empty lines, and move completed items to the bottom `## Done` section in `Todo.md`
- Weekly: If archival is needed, run the `todo-archival` skill instead of deleting done items directly here.
- Monthly: review category tracking notes
- Quarterly: archive completed projects and plan new ones
