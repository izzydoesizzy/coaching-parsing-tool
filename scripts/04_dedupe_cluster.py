#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

from pipeline_io import write_rows
from pipeline_utils import setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Canonicalize and dedupe extracted items")
    p.add_argument("--input", default="data/extractions.jsonl")
    p.add_argument("--questions-output", default="data/questions_canonical.csv")
    p.add_argument("--concerns-output", default="data/concerns_canonical.csv")
    p.add_argument("--advice-output", default="data/advice_library.csv")
    p.add_argument("--workflows-output", default="data/workflows_index.csv")
    p.add_argument("--themes-output", default="data/themes_dashboard.csv")
    p.add_argument("--similarity-threshold", type=float, default=0.83)
    return p.parse_args()


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def near(a: str, b: str, threshold: float) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def cluster_texts(items: list[dict], text_key: str, threshold: float) -> list[list[dict]]:
    clusters: list[list[dict]] = []
    for item in items:
        text = item.get(text_key, "").strip()
        if not text:
            continue
        placed = False
        for cluster in clusters:
            if near(text, cluster[0][text_key], threshold):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters


def canonical_row(cluster: list[dict], text_key: str, item_type: str) -> dict:
    counts = Counter(it[text_key] for it in cluster)
    canonical_text = counts.most_common(1)[0][0]
    variants = sorted(counts.keys())
    refs = [json.dumps(it.get("source_ref", {}), ensure_ascii=False) for it in cluster[:10]]
    return {
        "type": item_type,
        "canonical": canonical_text,
        "frequency": len(cluster),
        "variants": " | ".join(variants[:15]),
        "top_source_refs": " || ".join(refs),
        "confidence_avg": round(sum(float(it.get("confidence", 0.0)) for it in cluster) / max(1, len(cluster)), 3),
    }


def main() -> None:
    args = parse_args()
    setup_logging("04_dedupe_cluster")

    rows = load_jsonl(Path(args.input))

    questions, concerns, advice, workflows = [], [], [], []
    theme_counter = Counter()

    for row in rows:
        for q in row.get("questions", []):
            questions.append(q)
            theme_counter[q.get("ask_type", "other")] += 1
        for c in row.get("concerns", []):
            concerns.append(c)
        for a in row.get("advice", []):
            advice.append(a)
            for tag in a.get("category_tags", []):
                theme_counter[tag] += 1
        for w in row.get("workflows", []):
            workflows.append(w)

    q_clusters = cluster_texts(questions, "question_text", args.similarity_threshold)
    c_clusters = cluster_texts(concerns, "concern", args.similarity_threshold)
    a_clusters = cluster_texts(advice, "advice", args.similarity_threshold)
    w_clusters = cluster_texts(workflows, "title", args.similarity_threshold)

    questions_rows = [canonical_row(c, "question_text", "question") for c in q_clusters]
    concerns_rows = [canonical_row(c, "concern", "concern") for c in c_clusters]
    advice_rows = [canonical_row(c, "advice", "advice") for c in a_clusters]

    workflow_rows = []
    for c in w_clusters:
        row = canonical_row(c, "title", "workflow")
        sample = c[0]
        row["when_to_use"] = sample.get("when_to_use", "")
        row["steps"] = " | ".join(sample.get("steps", []))
        row["common_failure_modes"] = " | ".join(sample.get("common_failure_modes", []))
        row["scripts_templates"] = " | ".join(sample.get("scripts_templates", []))
        workflow_rows.append(row)

    total_theme = max(1, sum(theme_counter.values()))
    theme_rows = [{"theme": k, "frequency": v, "share": round(v / total_theme, 4)} for k, v in theme_counter.most_common()]

    write_rows(args.questions_output, questions_rows)
    write_rows(args.concerns_output, concerns_rows)
    write_rows(args.advice_output, advice_rows)
    write_rows(args.workflows_output, workflow_rows)
    write_rows(args.themes_output, theme_rows)


if __name__ == "__main__":
    main()
