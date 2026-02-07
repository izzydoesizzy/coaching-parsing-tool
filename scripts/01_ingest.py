#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from pipeline_io import read_rows, write_rows
from pipeline_utils import (
    ChunkConfig,
    chunk_text,
    dump_json,
    iter_transcript_files,
    load_json,
    normalize_whitespace,
    read_text_file,
    setup_logging,
    sha256_text,
    stable_id,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic transcript ingest + chunking")
    parser.add_argument("--transcripts-root", required=True)
    parser.add_argument("--output", default="data/ingest.parquet")
    parser.add_argument("--manifest", default="data/ingest_manifest.json")
    parser.add_argument("--chunk-tokens", type=int, default=1400)
    parser.add_argument("--overlap-ratio", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging("01_ingest")

    root = Path(args.transcripts_root)
    output_path = Path(args.output)
    manifest_path = Path(args.manifest)

    old_manifest = load_json(manifest_path, default={})
    try:
        existing_rows = read_rows(str(output_path))
    except FileNotFoundError:
        existing_rows = []

    cfg = ChunkConfig(chunk_tokens=args.chunk_tokens, overlap_ratio=args.overlap_ratio)

    all_rows: list[dict] = []
    unchanged_file_ids: set[str] = set()
    seen_paths: set[str] = set()

    files = sorted(set(iter_transcript_files(root)))
    logging.info("found %s transcript files", len(files))

    for file in files:
        raw = read_text_file(file)
        text = normalize_whitespace(raw)
        rel_path = str(file.relative_to(root))
        file_id = stable_id(rel_path)
        content_hash = sha256_text(text)
        mtime = file.stat().st_mtime
        seen_paths.add(rel_path)

        prior = old_manifest.get(rel_path)
        if prior and prior.get("content_hash") == content_hash:
            unchanged_file_ids.add(file_id)
            continue

        for chunk_text_value, start_offset, end_offset in chunk_text(text, cfg):
            chunk_hash = sha256_text(chunk_text_value)
            chunk_id = stable_id(file_id, str(start_offset), str(end_offset), chunk_hash)
            all_rows.append(
                {
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "file_path": rel_path,
                    "file_name": file.name,
                    "modified_time": mtime,
                    "content_hash": content_hash,
                    "text": chunk_text_value,
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                }
            )

        old_manifest[rel_path] = {
            "file_id": file_id,
            "content_hash": content_hash,
            "modified_time": mtime,
        }

    if existing_rows and unchanged_file_ids:
        reused = [r for r in existing_rows if r.get("file_id") in unchanged_file_ids]
        all_rows.extend(reused)
        logging.info("reused %s unchanged files from cache", len(unchanged_file_ids))

    for stale_path in list(old_manifest.keys()):
        if stale_path not in seen_paths:
            old_manifest.pop(stale_path, None)

    all_rows.sort(key=lambda r: (r.get("file_path", ""), int(r.get("start_offset", 0))))
    written_path = write_rows(str(output_path), all_rows)
    dump_json(manifest_path, old_manifest)

    logging.info(
        "wrote %s chunks across %s files to %s",
        len(all_rows),
        len({r.get('file_id') for r in all_rows}),
        written_path,
    )


if __name__ == "__main__":
    main()
