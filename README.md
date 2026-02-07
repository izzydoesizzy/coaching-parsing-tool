# ClearCareer Job-Search Transcript Mining Pipeline

This repository contains a rerunnable local Python pipeline to ingest transcript files, filter to job-search content, extract structured coaching intelligence, dedupe into canonical libraries, and generate final deliverables.

## Folder structure

- `scripts/01_ingest.py` — deterministic ingest with hashing, chunking, and cache reuse.
- `scripts/02_filter_jobsearch.py` — keyword (and optional LLM) relevance filter.
- `scripts/03_extract_llm.py` — strict JSON extraction of questions, concerns, advice, workflows.
- `scripts/04_dedupe_cluster.py` — canonicalization + near-duplicate clustering + frequency counts.
- `scripts/05_generate_outputs.py` — markdown and playbook deliverable generation.
- `data/` — parquet/jsonl/csv intermediate outputs.
- `outputs/` — final markdown reports and playbooks.
- `logs/` — run logs (`run_YYYYMMDD.log`).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If using OpenAI extraction/classification:

```bash
export OPENAI_API_KEY=your_key_here
```

## Run order

> Note: if `pandas/pyarrow` are unavailable, scripts automatically fall back to `.jsonl` files with the same basename.

```bash
python scripts/01_ingest.py --transcripts-root /path/to/transcripts
python scripts/02_filter_jobsearch.py --input data/ingest.parquet --output data/jobsearch_chunks.parquet
python scripts/03_extract_llm.py --input data/jobsearch_chunks.parquet --output data/extractions.jsonl
python scripts/04_dedupe_cluster.py --input data/extractions.jsonl
python scripts/05_generate_outputs.py
```

## Output contracts

Primary data outputs:

- `data/ingest.parquet`
- `data/jobsearch_chunks.parquet`
- `data/extractions.jsonl`
- `data/questions_canonical.csv`
- `data/concerns_canonical.csv`
- `data/advice_library.csv`
- `data/workflows_index.csv`
- `data/themes_dashboard.csv`

Final deliverables:

- `outputs/themes_summary.md`
- `outputs/overall_summary.md`
- `outputs/faq_raw.md`
- `outputs/faq_canonical.md`
- `outputs/advice_library.md`
- `outputs/playbooks/Playbook_*.md`

## Rerun behavior

- `01_ingest.py` computes `content_hash` per source file and reuses unchanged file chunks from previous `data/ingest.parquet`.
- `03_extract_llm.py` caches extraction by `(chunk_id, model, prompt_version)` to avoid paying twice.
- All downstream files can be regenerated deterministically from upstream artifacts.
