from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


def setup_logging(name: str) -> None:
    Path("logs").mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(f"logs/run_{stamp}.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.info("starting %s", name)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def stable_id(*parts: str) -> str:
    joined = "::".join(parts)
    return hashlib.sha1(joined.encode("utf-8", errors="ignore")).hexdigest()


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def iter_transcript_files(root: Path) -> Iterable[Path]:
    for ext in ("*.md", "*.markdown", "*.txt"):
        for file in root.rglob(ext):
            if file.is_file():
                yield file


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: dict | list):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict | list) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@dataclass
class ChunkConfig:
    chunk_tokens: int = 1400
    overlap_ratio: float = 0.15


def chunk_text(text: str, cfg: ChunkConfig) -> list[tuple[str, int, int]]:
    words = text.split()
    if not words:
        return []
    chunk_words = max(200, int(cfg.chunk_tokens / 1.3))
    overlap_words = int(chunk_words * cfg.overlap_ratio)
    step = max(1, chunk_words - overlap_words)

    chunks = []
    cursor = 0
    while cursor < len(words):
        window = words[cursor : cursor + chunk_words]
        if not window:
            break
        chunk = " ".join(window)
        chunks.append((chunk, cursor, cursor + len(window)))
        cursor += step
    return chunks
