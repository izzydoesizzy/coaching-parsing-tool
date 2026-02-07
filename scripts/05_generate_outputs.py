#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pipeline_io import markdown_table, read_rows
from pipeline_utils import setup_logging


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate markdown deliverables from canonical data")
    p.add_argument("--questions", default="data/questions_canonical.csv")
    p.add_argument("--concerns", default="data/concerns_canonical.csv")
    p.add_argument("--advice", default="data/advice_library.csv")
    p.add_argument("--workflows", default="data/workflows_index.csv")
    p.add_argument("--themes", default="data/themes_dashboard.csv")
    p.add_argument("--outputs-dir", default="outputs")
    return p.parse_args()


def sort_rows(rows: list[dict], key: str) -> list[dict]:
    return sorted(rows, key=lambda r: float(r.get(key, 0) or 0), reverse=True)


def main() -> None:
    args = parse_args()
    setup_logging("05_generate_outputs")

    out = Path(args.outputs_dir)
    playbooks_dir = out / "playbooks"
    out.mkdir(parents=True, exist_ok=True)
    playbooks_dir.mkdir(parents=True, exist_ok=True)

    questions = read_rows(args.questions)
    concerns = read_rows(args.concerns)
    advice = read_rows(args.advice)
    workflows = read_rows(args.workflows)
    themes = read_rows(args.themes)

    (out / "themes_summary.md").write_text(
        "# Themes Summary\n\n## Ranked Themes\n"
        + markdown_table(themes, ["theme", "frequency", "share"], 50)
        + "\n## Top Questions\n"
        + markdown_table(sort_rows(questions, "frequency"), ["canonical", "frequency", "variants"], 50),
        encoding="utf-8",
    )

    overall = (
        "# Overall Summary\n\n"
        f"- Canonical questions: {len(questions)}\n"
        f"- Canonical concerns: {len(concerns)}\n"
        f"- Canonical advice entries: {len(advice)}\n"
        f"- Workflow clusters: {len(workflows)}\n\n"
        "## What clients struggle with\n"
        + markdown_table(sort_rows(concerns, "frequency"), ["canonical", "frequency", "variants"], 30)
        + "\n## Common prescriptions\n"
        + markdown_table(sort_rows(advice, "frequency"), ["canonical", "frequency", "variants"], 30)
    )
    (out / "overall_summary.md").write_text(overall, encoding="utf-8")

    (out / "faq_canonical.md").write_text(
        "# Canonical FAQ\n\n" + markdown_table(sort_rows(questions, "frequency"), ["canonical", "frequency", "variants"], 500),
        encoding="utf-8",
    )
    (out / "advice_library.md").write_text(
        "# Advice Library\n\n" + markdown_table(sort_rows(advice, "frequency"), ["canonical", "frequency", "variants"], 500),
        encoding="utf-8",
    )

    (out / "faq_raw.md").write_text(
        "# Raw FAQ\n\nThis file is intended to contain every extracted raw question.\nUse `data/extractions.jsonl` as source for verbatim export.\n",
        encoding="utf-8",
    )

    for wf in workflows:
        safe_name = str(wf.get("canonical", "Workflow")).replace("/", "_").replace(" ", "_")[:80]
        path = playbooks_dir / f"Playbook_{safe_name}.md"
        steps = [s.strip() for s in str(wf.get("steps", "")).split("|") if s.strip()]
        fails = [s.strip() for s in str(wf.get("common_failure_modes", "")).split("|") if s.strip()]
        scripts = [s.strip() for s in str(wf.get("scripts_templates", "")).split("|") if s.strip()]
        body = (
            f"# {wf.get('canonical', 'Workflow')}\n\n"
            f"## When to use\n{wf.get('when_to_use', '')}\n\n"
            "## Steps\n"
            + "\n".join(f"- {s}" for s in steps)
            + "\n\n## Common failure modes\n"
            + "\n".join(f"- {s}" for s in fails)
            + "\n\n## Scripts/Templates\n"
            + "\n".join(f"- {s}" for s in scripts)
            + "\n\n## Versions\n- Minimum viable version: execute first 2-3 steps consistently.\n- Advanced version: instrument metrics and iterate weekly.\n"
        )
        path.write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
