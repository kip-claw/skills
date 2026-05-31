"""Offline tests for the audiobook pipeline. No network, no TTS calls."""
from __future__ import annotations

import sys
from pathlib import Path

# Make audiobook.py importable as a module without installing it.
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR))

import audiobook as ab  # noqa: E402


def test_slugify_basic():
    assert ab.slugify("Magnifica Humanitas") == "magnifica-humanitas"
    assert ab.slugify("  Hello, World! 2026  ") == "hello-world-2026"
    assert ab.slugify("???") == "audiobook"


def test_humanize_duration():
    assert ab.humanize_duration(0) == "0m"
    assert ab.humanize_duration(125) == "2m"
    assert ab.humanize_duration(3 * 3600 + 7 * 60 + 12) == "3h07m"


def test_pack_sentences_respects_max_chars():
    text = ". ".join(f"Sentence number {i}" for i in range(40)) + "."
    packed = ab._pack_sentences(text, max_chars=120)
    assert len(packed) > 1
    assert all(len(p) <= 120 for p in packed)
    # Round-trip: every sentence must still appear.
    rejoined = " ".join(packed)
    for i in range(40):
        assert f"Sentence number {i}" in rejoined


def test_pack_sentences_hard_wraps_long_sentence():
    long = "x" * 5000
    packed = ab._pack_sentences(long, max_chars=1000)
    assert len(packed) == 5
    assert all(len(p) == 1000 for p in packed)


def test_chunk_document_prepends_section_title():
    doc = ab.Document(
        title="Doc",
        author="A",
        sections=[ab.Section(title="Chapter One", text="Hello world. " * 30)],
    )
    chunks = ab.chunk_document(doc, max_chars=200, prepend_title=True)
    assert chunks
    assert chunks[0].text.startswith("Chapter One.")
    # Subsequent chunks of the same section do not repeat the title.
    if len(chunks) > 1:
        assert not chunks[1].text.startswith("Chapter One.")


def test_chunk_cache_key_is_stable_and_sensitive():
    k1 = ab._chunk_cache_key("openai", "alloy", 1.0, "hello")
    k2 = ab._chunk_cache_key("openai", "alloy", 1.0, "hello")
    k3 = ab._chunk_cache_key("openai", "nova", 1.0, "hello")
    k4 = ab._chunk_cache_key("openai", "alloy", 1.25, "hello")
    k5 = ab._chunk_cache_key("openai", "alloy", 1.0, "world")
    assert k1 == k2
    assert len({k1, k3, k4, k5}) == 4


def test_split_into_sections_creates_sections_from_short_lines():
    text = "Introduction\n\nThis is the body of the intro. It has stuff.\n\nChapter Two\n\nMore body text here."
    sections = ab._split_into_sections(text, doc_title="Doc")
    titles = [s.title for s in sections]
    assert "Introduction" in titles
    assert "Chapter Two" in titles


def test_load_config_resolves_tilde(tmp_path, monkeypatch):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("audio_dir: ~/audiobooks\nnested:\n  x: ~/foo\n")
    cfg = ab.load_config(cfg_file)
    assert "~" not in cfg["audio_dir"]
    assert "~" not in cfg["nested"]["x"]


def test_dry_run_does_not_call_tts(monkeypatch, tmp_path, capsys):
    # Build a fake doc; patch fetch/extract; ensure render_chunks is never invoked.
    def fake_fetch(url, timeout, retries):
        return b"<html><title>T</title><body>Hello world.</body></html>"

    fake_doc = ab.Document(
        title="Test Doc",
        author="Nobody",
        sections=[ab.Section(title="Test Doc", text="One. Two. Three. Four. Five.")],
    )

    def fake_extract(raw, url, content_type=None):
        return fake_doc

    def boom(*a, **kw):
        raise AssertionError("render_chunks must not be called in dry-run")

    monkeypatch.setattr(ab, "fetch", fake_fetch)
    monkeypatch.setattr(ab, "extract", fake_extract)
    monkeypatch.setattr(ab, "render_chunks", boom)

    rc = ab.main(["https://example.invalid/x", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "chunk ok" in out
    assert "Test Doc" in out
