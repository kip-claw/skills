---
name: kip-blog-post
description: Authors and publishes a new blog post on kip.computer, including lead art generation.
tag: Work
metadata: {"openclaw": {"emoji": "📝", "requires": {"bins": ["node", "npm", "ffmpeg", "git", "openclaw"]}}}
---

# Kip Blog Post

Write, illustrate, and publish a new entry on the kip.computer blog. The site is
a static SvelteKit project at `{{HOME}}/Code/kip-claw`; blog posts are mdsvex
Markdown files with YAML frontmatter, listed by a registry in `src/lib/posts.ts`
and rendered with a lead-art image.

Triggered when Ben asks to "write a blog post", "announce" something on
kip.computer, or publish a dispatch about a new app, skill, or project.

## Repository layout

- Repo: `{{HOME}}/Code/kip-claw`
- Post file: `src/routes/blog/<YYYY-MM-DD-slug>/+page.md`
- Post registry: `src/lib/posts.ts` (newest first)
- Lead art: `static/images/<slug-base>.jpg` plus `-1200.webp` and `-760.webp` variants
- Voice reference: `{{HOME}}/.openclaw/workspace/SOUL.md`

## Voice

Read `SOUL.md` and skim two or three recent posts under `src/routes/blog/`
before writing. Match Kip's established voice:

- First person, plainspoken, unhurried. Short declarative sentences.
- Frame work as small, durable plumbing that "makes the invisible visible."
- Ground details in Ben's life and the Raspberry Pi in Kips Bay when natural.
- An occasional, light nod to Rudyard Kipling — only when it fits, never forced.
- Honest and concrete about what a thing does and does not do.
- No marketing hype, no emoji, no exclamation points.

## Frontmatter schema

Every post `+page.md` begins with YAML frontmatter:

```yaml
---
title: Say the Word
deck: One-line summary shown under the title.
description: Slightly longer SEO/meta description (one or two sentences).
url: https://kip.computer/blog/<YYYY-MM-DD-slug>/
slug: <YYYY-MM-DD-slug>
leadArt:
  src: /images/<slug-base>.jpg
  alt: Descriptive alt text for the lead image.
  caption: Short caption shown beneath the lead image.
---
```

The body is Markdown. Mdsvex applies the `BlogPostLayout` automatically, which
renders the lead art from frontmatter — do not add an `<img>` for it in the body.

## Workflow

1. **Pick the slug and date.** Use `<YYYY-MM-DD>-<short-kebab-name>`, e.g.
   `2026-06-18-ask-kip`. The date is today's date.

2. **Draft the post.** Create
   `src/routes/blog/<slug>/+page.md` with the frontmatter above and the body in
   Kip's voice. Link to the relevant repo/app. Keep it tight — most posts are a
   few short paragraphs.

3. **Generate the lead art.** Use the OpenClaw image pipeline (same model the
   Bosch generator uses). Lead art is a photorealistic lobster in a scene that
   illustrates the post:

   ```bash
   cd {{HOME}}/Code/kip-claw
   openclaw infer image generate \
     --model "openai/gpt-image-2" \
     --size 1536x1024 \
     --output-format jpeg \
     --timeout-ms 240000 \
     --output "static/images/<slug-base>.jpg" \
     --prompt "<photorealistic prompt>" \
     --json
   ```

   Write a vivid, photojournalistic prompt. Confirm `"ok": true` in the JSON
   output and that the file was written.

4. **Make the webp variants.** The site expects `-1200.webp` and `-760.webp`
   alongside the jpg:

   ```bash
   {{HOME}}/.openclaw/workspace/skills/kip-blog-post/scripts/make-lead-art-variants.sh \
     static/images/<slug-base>.jpg
   ```

5. **Register the post.** Add an entry to the top of the `posts` array in
   `src/lib/posts.ts` (newest first). Use tabs for indentation to match the file:

   ```ts
   {
     slug: '<YYYY-MM-DD-slug>',
     title: '<title>',
     date: '<YYYY-MM-DD>',
     displayDate: '<Month D, YYYY>',
     description: '<one-sentence summary>'
   },
   ```

6. **Format and build to verify.**

   ```bash
   cd {{HOME}}/Code/kip-claw
   npx prettier --write "src/routes/blog/<slug>/+page.md" src/lib/posts.ts
   npm run build
   ```

   The build prerenders the post; confirm `build/blog/<slug>/index.html` exists
   and the post appears on `build/blog/index.html`.

7. **Commit and push.** A Husky pre-commit hook runs `svelte-check` and
   `prettier --check`, so the tree must be clean first.

   ```bash
   cd {{HOME}}/Code/kip-claw
   git add src/lib/posts.ts "src/routes/blog/<slug>/" \
     "static/images/<slug-base>.jpg" \
     "static/images/<slug-base>-1200.webp" \
     "static/images/<slug-base>-760.webp"
   git -c user.name='kip-claw' -c user.email='kip-claw@users.noreply.github.com' \
     commit -m "Add <slug-base> blog post"
   git push origin main
   ```

8. **Report.** Tell Ben the post title, the live URL
   (`https://kip.computer/blog/<slug>/`), and a one-line summary of the lead art.

## Notes

- Deploy is automatic from `main`; no manual deploy step.
- If `npm run build` fails, read the error, fix the frontmatter or registry
  entry, and rebuild before committing — never commit a broken build.
- Keep credentials and private machinery out of posts; publish the aggregate
  view, not the plumbing.
