---
name: "todo-archival"
description: "Cleans Todo.md by keeping completed items in one Done section until digest sweep."
title: Todo Cleanup
tag: Work
---

# Todo Cleanup

Todo file: `{{HOME}}/obsidian-vault/Todo.md`
Archive path: `{{HOME}}/obsidian-vault/Archive/Done-Items.md`

## Purpose

Keep `Todo.md` simple. Completed items live in one bottom `## Done` section until Ben confirms a News Apps digest has been sent or explicitly asks to archive/sweep them. The old `## Since Last Digest` buffer is deprecated and should not be recreated.

## Working rules

- Keep one `## Done` section at the bottom of `Todo.md`.
- Move checked items found in active sections (`## Work`, `## Teaching`, `## Home`, `## Open Source`) into `## Done`, preserving order, formatting, and hashtags.
- Do not create or use `## Since Last Digest`.
- Do not write to `Archive/Done-Items.md` during routine cleanup.
- Update the `modified:` frontmatter timestamp on `Todo.md` when items move or formatting changes.
- Leave the `## Done` header in place even when empty.

## Process

1. Read `{{HOME}}/obsidian-vault/Todo.md` completely.
2. Ensure there is a single `## Done` section at the bottom.
3. Remove any empty deprecated `## Since Last Digest` section if present.
4. Identify checked items (`- [x] ...`) under active sections.
5. Move those checked items into `## Done`.
6. Clean obvious whitespace issues and bump the `modified:` timestamp.
7. Validate tags with `kip-todo-lint` or equivalent taxonomy check.
8. Commit with message: `Clean up todo list`.

## Digest closeout

When Ben says a News Apps digest has been sent, use the `news-apps-digest` workflow to sweep `## Done` into `Archive/Done-Items.md` with `<!-- digest: YYYY-MM-DD -->` markers and leave `## Done` empty.
