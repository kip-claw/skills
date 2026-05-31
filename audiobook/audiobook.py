#!/usr/bin/env python3
"""Audiobook generator for OpenClaw.

Pipeline: fetch -> extract -> chunk -> TTS (pluggable provider) -> ffmpeg
concat -> tag. Per-chunk audio fragments are cached by content hash so
repeat runs only re-render changed sections.

Usage:
    audiobook.py <url> [--provider P] [--voice V] [--speed S]
                       [--format mp3|m4a] [--summary] [--podcast]
                       [--no-cache] [--dry-run] [--out PATH]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

SKILL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SKILL_DIR / "config.yaml"

log = logging.getLogger("audiobook")


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

def _expand_paths(node: Any) -> Any:
    if isinstance(node, str) and node.startswith("~"):
        return str(Path(node).expanduser())
    if isinstance(node, dict):
        return {k: _expand_paths(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_expand_paths(v) for v in node]
    return node


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return _expand_paths(yaml.safe_load(fh) or {})


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #

@dataclass
class Section:
    title: str
    text: str


@dataclass
class Document:
    title: str
    author: str
    sections: list[Section] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(s.text for s in self.sections)


def fetch(url: str, timeout: int, retries: int) -> bytes:
    import httpx

    # Some publishers (Reuters, NYT, etc.) hard-block bare scrapers. Send a
    # full browser-like header set so we get the same HTML a normal visitor
    # would. Still respects robots/paywalls — a 200 here just means the
    # public HTML loaded.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
    }
    transport = httpx.HTTPTransport(retries=retries)
    with httpx.Client(transport=transport, timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.content


def extract_html(raw: bytes, url: str) -> Document:
    import trafilatura
    from trafilatura.metadata import extract_metadata

    html = raw.decode("utf-8", errors="replace")
    text = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        favor_recall=True,
    ) or ""
    meta = extract_metadata(html, default_url=url)
    title = (meta.title if meta and meta.title else _fallback_title(html, url)).strip()
    author = (meta.author if meta and meta.author else "").strip()

    sections = _split_into_sections(text, title)
    return Document(title=title or "Untitled", author=author, sections=sections)


def extract_pdf(raw: bytes, url: str) -> Document:
    from pypdf import PdfReader

    with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
        fh.write(raw)
        fh.flush()
        reader = PdfReader(fh.name)
        meta = reader.metadata or {}
        title = (meta.get("/Title") or Path(url).stem or "Untitled").strip()
        author = (meta.get("/Author") or "").strip()
        pages = [(p.extract_text() or "").strip() for p in reader.pages]

    sections = [Section(title=f"Page {i + 1}", text=t) for i, t in enumerate(pages) if t]
    return Document(title=title, author=author, sections=sections)


def extract_epub(raw: bytes, url: str) -> Document:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    with tempfile.NamedTemporaryFile(suffix=".epub") as fh:
        fh.write(raw)
        fh.flush()
        book = epub.read_epub(fh.name)

    title = " ".join(t for t, _ in book.get_metadata("DC", "title")) or Path(url).stem
    author = ", ".join(a for a, _ in book.get_metadata("DC", "creator"))

    sections: list[Section] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        heading = soup.find(["h1", "h2"])
        sec_title = heading.get_text(strip=True) if heading else item.get_name()
        text = soup.get_text("\n", strip=True)
        if text:
            sections.append(Section(title=sec_title, text=text))

    return Document(title=title, author=author, sections=sections)


def extract(raw: bytes, url: str, content_type: str | None = None) -> Document:
    lower = url.lower()
    if lower.endswith(".pdf") or (content_type and "pdf" in content_type):
        return extract_pdf(raw, url)
    if lower.endswith(".epub") or (content_type and "epub" in content_type):
        return extract_epub(raw, url)
    return extract_html(raw, url)


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _fallback_title(html: str, url: str) -> str:
    match = _TITLE_RE.search(html)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return Path(url).stem.replace("-", " ").replace("_", " ").title()


_SECTION_BREAK = re.compile(r"\n{2,}")


def _split_into_sections(text: str, doc_title: str) -> list[Section]:
    if not text:
        return []
    blocks = [b.strip() for b in _SECTION_BREAK.split(text) if b.strip()]
    sections: list[Section] = []
    current_title = doc_title
    current_body: list[str] = []
    for block in blocks:
        if len(block) < 120 and not block.endswith((".", "!", "?", ":")) and "\n" not in block:
            # Treat short standalone lines as headings.
            if current_body:
                sections.append(Section(title=current_title, text="\n\n".join(current_body)))
                current_body = []
            current_title = block
            continue
        current_body.append(block)
    if current_body:
        sections.append(Section(title=current_title, text="\n\n".join(current_body)))
    return sections or [Section(title=doc_title, text=text)]


# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")


@dataclass
class Chunk:
    section_idx: int
    section_title: str
    text: str


def chunk_document(doc: Document, max_chars: int, prepend_title: bool) -> list[Chunk]:
    chunks: list[Chunk] = []
    for idx, section in enumerate(doc.sections):
        body = section.text.strip()
        if not body:
            continue
        pieces = _pack_sentences(body, max_chars)
        for i, piece in enumerate(pieces):
            text = piece
            if prepend_title and i == 0 and section.title and section.title != doc.title:
                text = f"{section.title}.\n\n{piece}"
            chunks.append(Chunk(section_idx=idx, section_title=section.title, text=text))
    return chunks


def _pack_sentences(text: str, max_chars: int) -> list[str]:
    sentences = _SENTENCE_RE.split(text)
    packed: list[str] = []
    buf: list[str] = []
    size = 0
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) > max_chars:
            # Hard-wrap an over-long "sentence" (e.g. URL-stuffed citation).
            if buf:
                packed.append(" ".join(buf))
                buf, size = [], 0
            for i in range(0, len(s), max_chars):
                packed.append(s[i : i + max_chars])
            continue
        if size + len(s) + 1 > max_chars and buf:
            packed.append(" ".join(buf))
            buf, size = [], 0
        buf.append(s)
        size += len(s) + 1
    if buf:
        packed.append(" ".join(buf))
    return packed


# --------------------------------------------------------------------------- #
# TTS
# --------------------------------------------------------------------------- #

def _chunk_cache_key(provider: str, voice: str, speed: float, text: str) -> str:
    h = hashlib.sha256()
    h.update(f"{provider}|{voice}|{speed:.3f}|".encode("utf-8"))
    h.update(text.encode("utf-8"))
    return h.hexdigest()


def render_chunks(
    chunks: Sequence[Chunk],
    config: dict[str, Any],
    provider: str,
    voice: str,
    speed: float,
    use_cache: bool,
) -> tuple[list[Path], dict[str, int]]:
    """Render each chunk to an MP3 fragment. Returns (paths, stats)."""
    from providers import load_provider  # lazy import; uses sibling module

    cache_dir = Path(config["cache"]["dir"]) if use_cache and config["cache"]["enabled"] else None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)

    fallbacks = config["provider"].get("fallbacks", [])
    order: list[str] = [provider] + [p for p in fallbacks if p != provider]

    # Ask the primary provider for a fingerprint that uniquely identifies the
    # actual narration model (e.g. for Piper the resolved voice file path).
    # Falls back to the abstract voice name when the provider doesn't expose
    # one or can't be instantiated yet.
    voice_key = voice
    try:
        from providers import load_provider as _load_provider  # lazy
        _primary = _load_provider(provider, config)
        fp = getattr(_primary, "cache_fingerprint", None)
        if callable(fp):
            voice_key = fp()
    except Exception:
        pass

    stats = {"total": len(chunks), "cached": 0, "rendered": 0, "failed": 0}
    paths: list[Path] = []
    last_provider_used = provider

    for ch in chunks:
        cache_path: Path | None = None
        if cache_dir:
            key = _chunk_cache_key(provider, voice_key, speed, ch.text)
            cache_path = cache_dir / f"{key}.mp3"
            if cache_path.exists() and cache_path.stat().st_size > 0:
                paths.append(cache_path)
                stats["cached"] += 1
                continue

        rendered_to: Path | None = None
        for prov in order:
            try:
                impl = load_provider(prov, config)
            except Exception as exc:
                log.warning("provider %s unavailable: %s", prov, exc)
                continue
            try:
                out_path = cache_path or Path(tempfile.mkstemp(suffix=".mp3")[1])
                impl.synthesize(text=ch.text, voice=voice, speed=speed, out_path=out_path)
                rendered_to = out_path
                last_provider_used = prov
                break
            except Exception as exc:
                log.warning("provider %s failed for chunk %d: %s", prov, len(paths), exc)
                continue

        if not rendered_to:
            stats["failed"] += 1
            raise RuntimeError(f"all TTS providers failed for chunk: {ch.text[:80]!r}")

        paths.append(rendered_to)
        stats["rendered"] += 1

    stats["provider"] = last_provider_used  # type: ignore[assignment]
    return paths, stats


# --------------------------------------------------------------------------- #
# Concat + tagging
# --------------------------------------------------------------------------- #

def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg not found on PATH; install with `sudo apt install ffmpeg`")
    return path


def concat_fragments(fragments: list[Path], out_path: Path, fmt: str) -> None:
    ffmpeg = _require_ffmpeg()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as listfile:
        for f in fragments:
            listfile.write(f"file '{f.as_posix()}'\n")
        list_path = listfile.name
    try:
        codec = "libmp3lame" if fmt == "mp3" else "aac"
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-c:a", codec, "-b:a", "64k",
            out_path.as_posix(),
        ]
        subprocess.run(cmd, check=True)
    finally:
        os.unlink(list_path)


def probe_duration_seconds(path: Path) -> float:
    ffprobe = shutil.which("ffprobe") or shutil.which("ffmpeg")
    if not ffprobe:
        return 0.0
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path.as_posix(),
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        return float(out)
    except Exception:
        return 0.0


def tag_output(path: Path, doc: Document, fmt: str) -> None:
    try:
        if fmt == "mp3":
            from mutagen.easyid3 import EasyID3
            from mutagen.mp3 import MP3
            audio = MP3(path.as_posix(), ID3=EasyID3)
            try:
                audio.add_tags()
            except Exception:
                pass
            audio["title"] = doc.title
            if doc.author:
                audio["artist"] = doc.author
            audio["album"] = "OpenClaw Audiobooks"
            audio.save()
        else:
            from mutagen.mp4 import MP4
            audio = MP4(path.as_posix())
            audio["\xa9nam"] = doc.title
            if doc.author:
                audio["\xa9ART"] = doc.author
            audio["\xa9alb"] = "OpenClaw Audiobooks"
            audio.save()
    except Exception as exc:
        log.warning("tagging failed: %s", exc)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-") or "audiobook"


def humanize_duration(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, _ = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"


def append_log(log_path: Path, entry: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


# --------------------------------------------------------------------------- #
# Optional features
# --------------------------------------------------------------------------- #

def maybe_summarize(text: str, config: dict[str, Any]) -> str:
    """Best-effort summary via OpenAI; pass text through if unavailable."""
    prompt = config["summary"].get("prompt", "")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text[:120_000]},
            ],
        )
        return (resp.choices[0].message.content or "").strip() or text
    except Exception as exc:
        log.warning("summary failed (%s); using full text", exc)
        return text


def maybe_append_rss(out_path: Path, doc: Document, duration: float, config: dict[str, Any]) -> None:
    cfg = config.get("rss", {})
    if not cfg.get("enabled"):
        return
    feed_path = Path(cfg["feed_path"])
    base_url = cfg["base_url"].rstrip("/") + "/"
    now = dt.datetime.now(dt.UTC).strftime("%a, %d %b %Y %H:%M:%S +0000")
    item = f"""
  <item>
    <title>{_xml_escape(doc.title)}</title>
    <author>{_xml_escape(doc.author or cfg.get('author', ''))}</author>
    <enclosure url=\"{base_url}{out_path.name}\" length=\"{out_path.stat().st_size}\" type=\"audio/mpeg\"/>
    <itunes:duration>{int(duration)}</itunes:duration>
    <pubDate>{now}</pubDate>
    <guid isPermaLink=\"false\">{out_path.stem}</guid>
  </item>
"""
    if not feed_path.exists():
        feed_path.parent.mkdir(parents=True, exist_ok=True)
        head = (
            f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            f"<rss version=\"2.0\" xmlns:itunes=\"http://www.itunes.com/dtds/podcast-1.0.dtd\">\n"
            f"<channel><title>{_xml_escape(cfg.get('title', 'Audiobooks'))}</title>\n"
        )
        feed_path.write_text(head + item + "</channel></rss>\n", encoding="utf-8")
    else:
        existing = feed_path.read_text(encoding="utf-8")
        feed_path.write_text(existing.replace("</channel>", item + "</channel>"), encoding="utf-8")


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace("\"", "&quot;").replace("'", "&apos;"))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="audiobook", description="Generate an audiobook from a URL.")
    p.add_argument("url", help="HTTP(S) URL to an article, PDF, or EPUB")
    p.add_argument("--provider", choices=["openai", "elevenlabs", "piper", "kokoro"], default=None)
    p.add_argument("--voice", default=None)
    p.add_argument("--speed", type=float, default=None)
    p.add_argument("--format", choices=["mp3", "m4a"], default=None)
    p.add_argument("--summary", action="store_true")
    p.add_argument("--podcast", action="store_true")
    p.add_argument("--no-cache", dest="no_cache", action="store_true")
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument("--out", default=None, help="Override output path")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )
    config = load_config()

    provider = args.provider or config["provider"]["default"]
    voice = args.voice or config.get("voice", "alloy")
    speed = args.speed if args.speed is not None else config.get("speed", 1.0)
    fmt = args.format or config.get("format", "mp3")

    # Phase 1: fetch
    raw = fetch(args.url, timeout=config["http"]["timeout_seconds"], retries=config["http"]["retries"])
    print(f"fetch ok bytes={len(raw)}")

    # Phase 2: extract
    doc = extract(raw, args.url)
    print(f'extract ok title="{doc.title}" author="{doc.author}" chars={len(doc.text)}')
    if not doc.sections:
        print("extract failed: no readable text", file=sys.stderr)
        return 2

    # Optional: summarize
    if args.summary or config["summary"].get("enabled"):
        summary_text = maybe_summarize(doc.text, config)
        doc.sections = [Section(title=doc.title, text=summary_text)]

    # Optional: podcast intro/outro
    if args.podcast or config["podcast"].get("enabled"):
        intro = config["podcast"]["intro"].format(title=doc.title, author=doc.author or "an unknown author")
        outro = config["podcast"]["outro"].format(title=doc.title)
        doc.sections.insert(0, Section(title="Intro", text=intro))
        doc.sections.append(Section(title="Outro", text=outro))

    # Phase 3: chunk
    chunks = chunk_document(
        doc,
        max_chars=int(config["chunk"]["max_chars"]),
        prepend_title=bool(config["chunk"]["prepend_section_title"]),
    )
    print(f"chunk ok sections={len(doc.sections)} chunks={len(chunks)} max_chars={config['chunk']['max_chars']}")

    if args.dry_run:
        print(json.dumps({"chunks": len(chunks), "sections": len(doc.sections), "title": doc.title}))
        return 0

    # Phase 4: TTS
    fragments, stats = render_chunks(
        chunks,
        config=config,
        provider=provider,
        voice=voice,
        speed=float(speed),
        use_cache=not args.no_cache,
    )
    print(
        f"tts provider={stats.get('provider', provider)} voice={voice} "
        f"chunks_total={stats['total']} cached={stats['cached']} rendered={stats['rendered']}"
    )

    # Phase 5: concat
    audio_dir = Path(config["audio_dir"])
    audio_dir.mkdir(parents=True, exist_ok=True)
    if args.out:
        out_path = Path(args.out).expanduser()
    else:
        name = config["filename_template"].format(
            date=dt.date.today().isoformat(),
            slug=slugify(doc.title),
            ext=fmt,
        )
        out_path = audio_dir / name
    concat_fragments(fragments, out_path, fmt=fmt)
    duration = probe_duration_seconds(out_path)
    print(f"concat ok duration={humanize_duration(duration)}")

    # Phase 6: tag
    tag_output(out_path, doc, fmt=fmt)
    print(f"tag ok format={fmt} path={out_path}")

    # Optional: RSS
    maybe_append_rss(out_path, doc, duration, config)

    # Log + JSON summary
    summary = {
        "title": doc.title,
        "author": doc.author,
        "duration_seconds": int(duration),
        "runtime": humanize_duration(duration),
        "path": str(out_path),
        "chapters": len(doc.sections),
        "provider": stats.get("provider", provider),
        "voice": voice,
        "chunks_total": stats["total"],
        "cached": stats["cached"],
        "rendered": stats["rendered"],
    }
    append_log(Path(config["log_path"]), {"ts": dt.datetime.now(dt.UTC).isoformat(), "url": args.url, **summary})
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
