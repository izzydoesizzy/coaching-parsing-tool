#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from pipeline_io import read_rows
from pipeline_utils import ensure_parent, load_json, setup_logging, stable_id


SCHEMA = {
    "questions": [{"question_text": "", "ask_type": "", "speaker": "", "confidence": 0.0, "source_ref": {}}],
    "concerns": [{"concern": "", "context": "", "emotion": "", "confidence": 0.0, "source_ref": {}}],
    "advice": [{"advice": "", "category_tags": [], "intended_outcome": "", "confidence": 0.0, "source_ref": {}}],
    "workflows": [
        {
            "title": "",
            "when_to_use": "",
            "steps": [],
            "common_failure_modes": [],
            "scripts_templates": [],
            "confidence": 0.0,
            "source_ref": {},
        }
    ],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract questions/concerns/advice/workflows from chunks")
    p.add_argument("--input", default="data/jobsearch_chunks.parquet")
    p.add_argument("--output", default="data/extractions.jsonl")
    p.add_argument("--cache", default="data/extraction_cache.json")
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--rule-based", action="store_true", help="Use local heuristic extraction")
    return p.parse_args()


def classify_ask_type(q: str) -> str:
    ql = q.lower()
    mapping = {
        "resume": ["resume", "cv", "ats"],
        "linkedin": ["linkedin", "profile"],
        "networking": ["network", "outreach", "referral"],
        "interviewing": ["interview"],
        "negotiation": ["offer", "salary", "negot"],
        "applications": ["apply", "application", "hiring manager"],
        "mindset": ["confidence", "anxiety", "stuck", "burnout"],
        "strategy": ["plan", "strategy", "prioritize"],
    }
    for tag, terms in mapping.items():
        if any(t in ql for t in terms):
            return tag
    return "other"


def heuristic_extract(text: str, source_ref: dict) -> dict:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    questions, concerns, advice = [], [], []
    for sent in sentences:
        clean = sent.strip()
        if not clean:
            continue
        if clean.endswith("?"):
            questions.append({"question_text": clean, "ask_type": classify_ask_type(clean), "speaker": "unknown", "confidence": 0.55, "source_ref": source_ref})
        if any(k in clean.lower() for k in ["worried", "struggling", "stuck", "concern", "afraid"]):
            concerns.append({"concern": clean, "context": "", "emotion": "", "confidence": 0.5, "source_ref": source_ref})
        if any(k in clean.lower() for k in ["should", "recommend", "try", "focus on", "need to"]):
            advice.append({"advice": clean, "category_tags": [classify_ask_type(clean)], "intended_outcome": "", "confidence": 0.5, "source_ref": source_ref})

    workflows = []
    numbered_lines = [ln.strip() for ln in text.splitlines() if re.match(r"^\d+[.)]\s+", ln.strip())]
    if len(numbered_lines) >= 3:
        workflows.append({"title": "Extracted workflow", "when_to_use": "When facing related job-search scenario", "steps": numbered_lines, "common_failure_modes": [], "scripts_templates": [], "confidence": 0.45, "source_ref": source_ref})

    return {"questions": questions, "concerns": concerns, "advice": advice, "workflows": workflows}




def _extract_output_text(response: Any) -> str:
    text = (getattr(response, "output_text", "") or "").strip()
    if text:
        return text

    output = getattr(response, "output", None) or []
    chunks: list[str] = []
    for item in output:
        for content in getattr(item, "content", None) or []:
            if getattr(content, "type", None) in {"output_text", "text"} and getattr(content, "text", None):
                chunks.append(content.text)
    return "\n".join(chunks).strip()


def _extract_json_payload(response: Any) -> dict:
    payload = _extract_output_text(response)
    if not payload:
        raise ValueError("empty text payload from model response")

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", payload, re.DOTALL | re.IGNORECASE)
        if match:
            return json.loads(match.group(1))
        raise

def llm_extract(model: str, text: str, source_ref: dict) -> dict:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    instruction = (
        "Extract coaching data into strict JSON with exactly these top-level keys: questions, concerns, advice, workflows. No prose.\n"
        "Attach source_ref to every object using this exact source_ref: "
        f"{json.dumps(source_ref)}\nSchema example:\n{json.dumps(SCHEMA)}\nUse empty arrays if none found."
    )
    response = client.responses.create(model=model, input=f"{instruction}\n\nChunk:\n{text[:9000]}")
    return _extract_json_payload(response)


def main() -> None:
    args = parse_args()
    setup_logging("03_extract_llm")

    rows = read_rows(args.input)
    cache_path = Path(args.cache)
    cache = load_json(cache_path, default={})

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            source_ref = {
                "file_id": row.get("file_id", ""),
                "chunk_id": row.get("chunk_id", ""),
                "start_offset": int(row.get("start_offset", 0)),
                "end_offset": int(row.get("end_offset", 0)),
                "file_path": row.get("file_path", ""),
            }
            key = stable_id(str(row.get("chunk_id", "")), args.model, "v1")
            if key in cache:
                extracted = cache[key]
            else:
                if args.rule_based or not os.getenv("OPENAI_API_KEY"):
                    extracted = heuristic_extract(str(row.get("text", "")), source_ref)
                else:
                    try:
                        extracted = llm_extract(args.model, str(row.get("text", "")), source_ref)
                    except Exception as exc:  # noqa: BLE001
                        message = str(exc)
                        if "insufficient_quota" in message:
                            logging.warning("OpenAI quota unavailable; switching to heuristic extraction for remaining chunks")
                            args.rule_based = True
                        logging.warning("LLM extraction failed for %s, using heuristic: %s", row.get("chunk_id"), exc)
                        extracted = heuristic_extract(str(row.get("text", "")), source_ref)
                cache[key] = extracted

            record = {
                "chunk_id": row.get("chunk_id", ""),
                "file_id": row.get("file_id", ""),
                "file_path": row.get("file_path", ""),
                "source_ref": source_ref,
                "questions": extracted.get("questions", []),
                "concerns": extracted.get("concerns", []),
                "advice": extracted.get("advice", []),
                "workflows": extracted.get("workflows", []),
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    ensure_parent(cache_path)
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    logging.info("wrote extraction output to %s", output_path)


if __name__ == "__main__":
    main()
