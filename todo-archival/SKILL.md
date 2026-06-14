---
name: todo-archival
title: Todo Cleanup
description: Moves completed to-do items into an archive buffer for the next digest.
tag: Work
---

# Todo Archival

Buffer section: `## Since Last Digest` in `{{HOME}}/obsidian-vault/Todo.md`
Archive path: `{{HOME}}/obsidian-vault/Archive/Done-Items.md`
Todo file: `{{HOME}}/obsidian-vault/Todo.md`

## Purpose

Keep the active `## Work`/`## Teaching`/`## Home`/`## Open Source` lists clean by moving checked items out of the `## Done` section into the `## Since Last Digest` buffer. The buffer is the source of truth for what's shipped between digests; the `news-apps-digest` skill reads from it when drafting and flushes it to the monthly archive when Ben confirms a digest has been sent.

**Important:** This skill no longer archives directly to `Archive/Done-Items.md`. That responsibility moved to `news-apps-digest` so digests and archived items stay in sync.

## Working rules

- Move checked items from `## Done` into `## Since Last Digest`, preserving order, formatting, and all hashtags
- Do not touch items already in `## Since Last Digest`
- Do not write to `Archive/Done-Items.md` (that's `news-apps-digest`'s job after a digest is sent)
- Update the `modified:` frontmatter timestamp on `Todo.md` when items move
- Leave the `## Done` header in place (it stays empty between runs and that's fine)

## Process

1. Read `{{HOME}}/obsidian-vault/Todo.md` completely
2. Identify checked items (`- [x] ...`) under the `## Done` section
3. If there are no checked items, exit cleanly — nothing to do
4. Append those items to the bottom of the `## Since Last Digest` section (above `## Done`)
5. Remove them from `## Done`
6. Bump the `modified:` timestamp in the frontmatter
7. Commit with message: `Move completed items into Since Last Digest buffer`

## Why this changed

Originally, this skill flushed checked items straight into a monthly section of `Archive/Done-Items.md`. That made "what's been shipped since the last digest" hard to reconstruct — it required diffing the archive across an arbitrary cadence. Now the buffer is explicit, visible in Obsidian, and tied 1:1 to a digest's lifecycle.

## Notes

- If you find yourself wanting to push items into `Archive/Done-Items.md` directly (e.g., Ben requests "archive everything in the buffer"), call `news-apps-digest` with a flush flag — don't bypass it. The digest skill stamps each archived line with a `<!-- digest: YYYY-MM-DD -->` marker so future skills can reconstruct which digest absorbed which item.
