from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_rows(path_str: str) -> list[dict]:
    path = Path(path_str)
    try:
        import pandas as pd

        if path.exists() and path.suffix == ".parquet":
            return pd.read_parquet(path).to_dict("records")
        if path.exists() and path.suffix == ".csv":
            return pd.read_csv(path).to_dict("records")
    except Exception:
        pass

    if path.exists():
        return _read_jsonl(path)

    if path.suffix in {".parquet", ".csv"}:
        alt = path.with_suffix(".jsonl")
        if alt.exists():
            logging.warning("tabular file unavailable; reading fallback %s", alt)
            return _read_jsonl(alt)
    raise FileNotFoundError(path)


def write_rows(path_str: str, rows: list[dict]) -> Path:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import pandas as pd

        df = pd.DataFrame(rows)
        if path.suffix == ".parquet":
            df.to_parquet(path, index=False)
            return path
        if path.suffix == ".csv":
            df.to_csv(path, index=False)
            return path
    except Exception as exc:
        logging.warning("tabular writer fallback to jsonl: %s", exc)

    if path.suffix in {".parquet", ".csv"}:
        path = path.with_suffix(".jsonl")
    _write_jsonl(path, rows)
    return path


def markdown_table(rows: list[dict], columns: list[str], max_rows: int = 50) -> str:
    if not rows:
        return "_No records found._\n"
    shown = rows[:max_rows]
    header = "| " + " | ".join(columns) + " |\n"
    sep = "|" + "|".join(["---" for _ in columns]) + "|\n"
    body = ""
    for row in shown:
        body += "| " + " | ".join(str(row.get(c, "")) for c in columns) + " |\n"
    return header + sep + body
