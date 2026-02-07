#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path

from pipeline_io import read_rows, write_rows
from pipeline_utils import setup_logging

DEFAULT_KEYWORDS = [
    "resume",
    "cv",
    "ats",
    "linkedin",
    "recruiter",
    "referral",
    "networking",
    "outreach",
    "interview",
    "offer",
    "negotiation",
    "application",
    "hiring manager",
    "follow-up",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter chunks to job-search content")
    parser.add_argument("--input", default="data/ingest.parquet")
    parser.add_argument("--output", default="data/jobsearch_chunks.parquet")
    parser.add_argument("--keywords-json", help="optional JSON list of keywords")
    parser.add_argument("--min-keyword-hits", type=int, default=1)
    parser.add_argument("--use-llm", action="store_true")
    parser.add_argument("--model", default="gpt-4o-mini")
    return parser.parse_args()


def compile_keywords(custom_json: str | None) -> list[str]:
    if custom_json:
        return json.loads(custom_json)
    return DEFAULT_KEYWORDS


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [kw for kw in keywords if re.search(rf"\b{re.escape(kw.lower())}\b", lowered)]


def llm_is_jobsearch(model: str, text: str) -> bool:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = (
        "Classify if this transcript chunk is about job-search coaching. "
        "Return only JSON: {\"job_search\": true|false}.\n\n"
        f"Chunk:\n{text[:4000]}"
    )
    resp = client.responses.create(model=model, input=prompt)
    payload = resp.output_text.strip()
    try:
        data = json.loads(payload)
        return bool(data.get("job_search", False))
    except json.JSONDecodeError:
        logging.warning("LLM classifier returned invalid JSON: %s", payload)
        return False


def main() -> None:
    args = parse_args()
    setup_logging("02_filter_jobsearch")

    keywords = compile_keywords(args.keywords_json)
    rows = read_rows(args.input)
    filtered: list[dict] = []

    for row in rows:
        hits = keyword_hits(str(row.get("text", "")), keywords)
        row["keyword_hits"] = hits
        row["keyword_score"] = len(hits)
        if row["keyword_score"] < args.min_keyword_hits:
            continue
        if args.use_llm:
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY must be set when --use-llm is enabled")
            row["llm_jobsearch"] = llm_is_jobsearch(args.model, str(row.get("text", "")))
            if not row["llm_jobsearch"]:
                continue
        else:
            row["llm_jobsearch"] = None
        filtered.append(row)

    written = write_rows(args.output, filtered)
    logging.info("kept %s/%s chunks -> %s", len(filtered), len(rows), written)


if __name__ == "__main__":
    main()
