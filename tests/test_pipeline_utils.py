from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pipeline_utils import ChunkConfig, chunk_text, normalize_whitespace, sha256_text, stable_id


def test_sha256_text_is_deterministic():
    assert sha256_text("hello") == sha256_text("hello")
    assert len(sha256_text("hello")) == 64


def test_stable_id_changes_when_input_changes():
    first = stable_id("file", "1")
    second = stable_id("file", "2")
    assert first != second


def test_normalize_whitespace():
    assert normalize_whitespace("  hello\n\nworld   ") == "hello world"


def test_chunk_text_returns_empty_list_for_empty_input():
    cfg = ChunkConfig(chunk_tokens=500, overlap_ratio=0.2)
    assert chunk_text("", cfg) == []


def test_chunk_text_creates_multiple_windows_for_long_text():
    cfg = ChunkConfig(chunk_tokens=260, overlap_ratio=0.2)
    text = " ".join([f"word{i}" for i in range(1000)])
    chunks = chunk_text(text, cfg)

    assert len(chunks) > 1
    assert chunks[0][1] == 0
    assert chunks[1][1] > chunks[0][1]
