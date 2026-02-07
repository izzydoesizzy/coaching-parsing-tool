# ClearCareer Coaching Parsing Tool

A beginner-friendly, step-by-step pipeline that reads coaching transcripts and turns them into structured reports you can use immediately.

---

## What this project does (in plain English)

This tool takes messy transcript text files and helps you answer:

- What questions people ask most often
- What worries or concerns come up repeatedly
- What advice appears most often
- What repeatable workflows are mentioned

It then creates clean files and Markdown reports in the `outputs/` folder.

---

## Who this README is for

This guide is written for people with **very little coding experience**.

If you can copy/paste terminal commands, you can run this project.

---

## Quick start (copy/paste only)

> Replace `/ABSOLUTE/PATH/TO/YOUR/TRANSCRIPTS` with your real folder path.

```bash
# 1) Move into the project
cd /workspace/coaching-parsing-tool

# 2) Create a Python virtual environment (isolated package space)
python -m venv .venv

# 3) Activate the environment
source .venv/bin/activate

# 4) Install dependencies
pip install -r requirements.txt

# 5) (Optional, for OpenAI-powered extraction) add your API key
export OPENAI_API_KEY="sk-your-real-openai-key"

# 6) Run all pipeline steps with a colorful, verbose runner
bash scripts/run_pipeline_verbose.sh /ABSOLUTE/PATH/TO/YOUR/TRANSCRIPTS
```

When it finishes, open the `outputs/` folder.

---

## Exactly which API key you need

### Required API keys

- **`OPENAI_API_KEY`** (only required if you want OpenAI model extraction/classification).

### Where to put it

In the terminal session right before running the pipeline:

```bash
export OPENAI_API_KEY="sk-your-real-openai-key"
```

### Important behavior

- If `OPENAI_API_KEY` is not set, extraction can still run with built-in rule-based logic.
- If you explicitly pass `--use-llm` in step 2 filtering and no key is set, it will fail by design.

---

## Project structure

- `scripts/01_ingest.py` → reads transcript files and chunks text
- `scripts/02_filter_jobsearch.py` → keeps job-search-related chunks
- `scripts/03_extract_llm.py` → extracts structured coaching info
- `scripts/04_dedupe_cluster.py` → deduplicates and clusters similar entries
- `scripts/05_generate_outputs.py` → writes Markdown deliverables
- `scripts/run_pipeline_verbose.sh` → colorful one-command runner
- `tests/` → automated tests for TDD workflow
- `data/` → intermediate generated files
- `outputs/` → final human-readable reports
- `logs/` → timestamped run logs

---

## Full execution guide (very detailed)

## 0) Prepare transcripts

Put your transcript files in one folder. Supported file types:

- `.txt`
- `.md`
- `.markdown`

Example:

```text
/home/you/transcripts/
  call_001.txt
  call_002.md
  onboarding.markdown
```

## 1) Setup environment

```bash
cd /workspace/coaching-parsing-tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2) Choose extraction mode

### Option A: OpenAI extraction (recommended quality)

```bash
export OPENAI_API_KEY="sk-your-real-openai-key"
```

Then run normal verbose pipeline:

```bash
bash scripts/run_pipeline_verbose.sh /home/you/transcripts
```

### Option B: Local rule-based extraction (no API key)

```bash
USE_RULE_BASED=1 bash scripts/run_pipeline_verbose.sh /home/you/transcripts
```

## 3) Optional: run each step manually (advanced)

```bash
python scripts/01_ingest.py --transcripts-root /home/you/transcripts --output data/ingest.parquet
python scripts/02_filter_jobsearch.py --input data/ingest.parquet --output data/jobsearch_chunks.parquet
python scripts/03_extract_llm.py --input data/jobsearch_chunks.parquet --output data/extractions.jsonl
python scripts/04_dedupe_cluster.py --input data/extractions.jsonl
python scripts/05_generate_outputs.py
```

---

## Test-Driven Development (TDD) workflow

This repository includes automated tests so changes can be made safely.

### Run tests first (red/green cycle)

```bash
# Run all tests with verbose output
pytest -vv
```

### Suggested TDD cycle

1. Write or update a failing test in `tests/`.
2. Run `pytest -vv` and confirm it fails.
3. Implement a minimal code fix.
4. Run `pytest -vv` until all tests pass.
5. Refactor if needed and run tests again.

### Useful test commands

```bash
# Run one test file only
pytest -vv tests/test_pipeline_utils.py

# Stop at first failure (fast feedback)
pytest -vv -x

# Re-run only failed tests from previous run
pytest -vv --lf
```

---

## What outputs you get

Main data files (in `data/`):

- `ingest.parquet` (or `ingest.jsonl` fallback)
- `jobsearch_chunks.parquet` (or `.jsonl` fallback)
- `extractions.jsonl`
- `questions_canonical.csv`
- `concerns_canonical.csv`
- `advice_library.csv`
- `workflows_index.csv`
- `themes_dashboard.csv`

Human-readable reports (in `outputs/`):

- `themes_summary.md`
- `overall_summary.md`
- `faq_raw.md`
- `faq_canonical.md`
- `advice_library.md`
- `outputs/playbooks/Playbook_*.md`

---

## Troubleshooting

### “Command not found: pytest”

You likely did not install dependencies inside the virtual environment.

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### “OPENAI_API_KEY must be set”

You enabled an LLM mode without setting the key.

Fix:

```bash
export OPENAI_API_KEY="sk-your-real-openai-key"
```

Or run rule-based mode:

```bash
USE_RULE_BASED=1 bash scripts/run_pipeline_verbose.sh /home/you/transcripts
```

### Missing `.parquet` support

The scripts already include JSONL fallback behavior. If parquet dependencies are unavailable, outputs may be written as `.jsonl` instead.

---

## Best-practice development checklist

Before creating a pull request:

```bash
# 1) Run tests
pytest -vv

# 2) Run the pipeline on a small sample transcript folder
USE_RULE_BASED=1 bash scripts/run_pipeline_verbose.sh /home/you/transcripts_sample
```

If both succeed, your changes are likely safe to merge.
