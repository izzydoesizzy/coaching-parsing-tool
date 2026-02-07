#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_banner() {
  echo -e "${PURPLE}${BOLD}==============================================================${NC}"
  echo -e "${PURPLE}${BOLD}      🚀 ClearCareer Pipeline Runner (Verbose + Friendly)      ${NC}"
  echo -e "${PURPLE}${BOLD}==============================================================${NC}"
}

progress_bar() {
  local width=32
  local i
  for ((i = 0; i <= width; i++)); do
    local done_bar
    done_bar=$(printf '%*s' "$i" '' | tr ' ' '█')
    local todo_bar
    todo_bar=$(printf '%*s' "$((width - i))" '' | tr ' ' '░')
    local pct=$((i * 100 / width))
    printf "\r${CYAN}[%s%s] %3d%%${NC}" "$done_bar" "$todo_bar" "$pct"
    sleep 0.02
  done
  echo
}

run_step() {
  local name="$1"
  local command="$2"

  echo -e "\n${BLUE}${BOLD}▶ Step:${NC} ${BOLD}${name}${NC}"
  echo -e "${YELLOW}Command:${NC} ${command}"
  echo -e "${CYAN}Status:${NC} Starting now..."
  progress_bar

  if eval "$command"; then
    echo -e "${GREEN}✅ Completed:${NC} ${name}"
  else
    echo -e "${RED}❌ Failed:${NC} ${name}"
    exit 1
  fi
}

TRANSCRIPTS_ROOT=${1:-}
if [[ -z "${TRANSCRIPTS_ROOT}" ]]; then
  echo -e "${RED}Usage:${NC} bash scripts/run_pipeline_verbose.sh /absolute/path/to/transcripts"
  exit 1
fi

print_banner

echo -e "${CYAN}📁 Transcript folder:${NC} ${TRANSCRIPTS_ROOT}"

echo -e "${YELLOW}Tip:${NC} If you want to force rule-based extraction, set USE_RULE_BASED=1"

FILTER_CMD="python scripts/02_filter_jobsearch.py --input data/ingest.parquet --output data/jobsearch_chunks.parquet"
EXTRACT_CMD="python scripts/03_extract_llm.py --input data/jobsearch_chunks.parquet --output data/extractions.jsonl"
if [[ "${USE_RULE_BASED:-0}" == "1" ]]; then
  EXTRACT_CMD+=" --rule-based"
fi

run_step "Ingest transcript files" \
  "python scripts/01_ingest.py --transcripts-root '${TRANSCRIPTS_ROOT}' --output data/ingest.parquet"
run_step "Filter to job-search content" "${FILTER_CMD}"
run_step "Extract questions/concerns/advice/workflows" "${EXTRACT_CMD}"
run_step "Deduplicate and cluster similar items" \
  "python scripts/04_dedupe_cluster.py --input data/extractions.jsonl"
run_step "Generate final markdown deliverables" \
  "python scripts/05_generate_outputs.py"

echo -e "\n${GREEN}${BOLD}🎉 Pipeline run finished successfully!${NC}"
echo -e "${CYAN}Next:${NC} open the ${BOLD}outputs/${NC} folder to read the reports."
