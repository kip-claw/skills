---
name: todo-archival
description: Archives completed Todo.md items into Archive/Done-Items.md to keep the active task list clean.
---

# Todo Archival

Archive path: `{{HOME}}/obsidian-vault/Archive/Done-Items.md`
Todo file: `{{HOME}}/obsidian-vault/Todo.md`

## Purpose

Nightly archival keeps the main Todo.md file clean and focused by moving completed items to a permanent archive file.

## Working rules

- Archive done items to Archive/Done-Items.md organized by month
- Preserve all formatting and hashtags when archiving
- Update frontmatter timestamps when editing Todo.md

## Archive file format

The Done-Items archive uses monthly sections:

```markdown
---
created: '<ISO timestamp>'
modified: '<ISO timestamp>'
---

# Done Items Archive

## May 2026
- [x] Item with #tag
- [x] Another completed item

## April 2026
- [x] Older completed item
```

When adding a new month section, add it at the top (most recent first).

## Process

1. Read `{{HOME}}/obsidian-vault/Todo.md` completely
2. Identify items in the `## Done` section that are checked off
3. If Archive/Done-Items.md doesn't exist, create it with proper frontmatter
4. Move archived items to the archive file (newest month at top)
5. Update the `modified` timestamp in frontmatter for both files
7. Commit changes with message: "Archive done items from todo list"
