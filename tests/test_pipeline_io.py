from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from pipeline_io import markdown_table, read_rows, write_rows


def test_markdown_table_empty_message():
    result = markdown_table([], ["a", "b"])
    assert "No records found" in result


def test_markdown_table_includes_headers_and_row_values():
    rows = [{"name": "Ada", "score": 10}]
    table = markdown_table(rows, ["name", "score"])

    assert "| name | score |" in table
    assert "| Ada | 10 |" in table


def test_write_and_read_jsonl_round_trip(tmp_path: Path):
    output = tmp_path / "sample.jsonl"
    rows = [{"id": 1, "text": "hello"}, {"id": 2, "text": "world"}]

    write_rows(str(output), rows)
    loaded = read_rows(str(output))

    assert loaded == rows


def test_read_rows_uses_jsonl_fallback_for_missing_parquet(tmp_path: Path):
    parquet_path = tmp_path / "ingest.parquet"
    jsonl_fallback = tmp_path / "ingest.jsonl"
    jsonl_fallback.write_text('{"id": 1, "text": "fallback"}\n', encoding="utf-8")

    loaded = read_rows(str(parquet_path))

    assert loaded == [{"id": 1, "text": "fallback"}]
