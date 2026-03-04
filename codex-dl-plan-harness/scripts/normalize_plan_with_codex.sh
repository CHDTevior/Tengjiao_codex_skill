#!/usr/bin/env bash
set -euo pipefail

PLAN=""
TARGET="$(pwd)"
OUT=""
REPORT=""
MODEL="${CODEX_PLAN_MODEL:-}"
LOG_PATH=""

usage() {
  cat <<'EOF'
Usage:
  normalize_plan_with_codex.sh --plan PLAN_FILE [--target TARGET_DIR] [--out NORMALIZED_PLAN] [--report REPORT_MD] [--model MODEL] [--log LOG_FILE]

Description:
  Use Codex to rewrite a free-form DL research plan into a deterministic markdown structure
  that is easier for rule-based extraction.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan)
      PLAN="$2"
      shift 2
      ;;
    --target|--project-root)
      TARGET="$2"
      shift 2
      ;;
    --out)
      OUT="$2"
      shift 2
      ;;
    --report)
      REPORT="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --log)
      LOG_PATH="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PLAN" ]]; then
  echo "[error] --plan is required" >&2
  exit 1
fi

if [[ ! -f "$PLAN" ]]; then
  echo "[error] plan file does not exist: $PLAN" >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "[error] codex CLI is not available in PATH" >&2
  exit 1
fi

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"
PLAN="$(cd "$(dirname "$PLAN")" && pwd)/$(basename "$PLAN")"

if [[ -z "$OUT" ]]; then
  OUT="$TARGET/.codex-research/plan/normalized_plan.md"
fi
if [[ -z "$REPORT" ]]; then
  REPORT="$TARGET/.codex-research/plan/alignment_report.md"
fi
if [[ -z "$LOG_PATH" ]]; then
  LOG_PATH="$TARGET/.codex-research/plan/codex_normalize.log"
fi

mkdir -p "$(dirname "$OUT")" "$(dirname "$REPORT")" "$(dirname "$LOG_PATH")"

TMP_DIR="$(mktemp -d)"
PROMPT_PATH="$TMP_DIR/prompt.txt"
RAW_OUTPUT="$TMP_DIR/raw_output.txt"
trap 'rm -rf "$TMP_DIR"' EXIT

cat > "$PROMPT_PATH" <<'EOF'
You are preparing a deep-learning research plan for deterministic rule-based parsing.

Task:
Rewrite the source plan into a normalized markdown document while preserving the original intent.

Hard requirements:
1. Return only markdown text. No code fences, no XML, no explanation outside the markdown.
2. Keep the exact section order and titles below:
   # Normalized Research Plan
   ## Objectives
   ## Constraints
   ## Environment and Resources
   ## Milestones
   ## Task Checklist
   ## Evaluation and Success Criteria
   ## Execution Signals
   ## Risks and Mitigations
   ## Open Questions
   ## Source Mapping
3. Under "Task Checklist", every item must be a markdown checkbox: "- [ ] ...".
4. Under "Execution Signals", list only applicable signals as bullet items in format:
   - <signal>: <short reason>
   Allowed signal names: slurm, wandb, huggingface, webdataset, evaluation, inference.
   If none apply, write exactly: "- none".
5. Do not invent concrete experimental results, datasets, or hard constraints not present in the source.
6. If the source is ambiguous, keep uncertainty in "Open Questions" instead of guessing.
7. In "Source Mapping", map major normalized items back to specific source fragments.

Source plan begins below:
EOF
printf '\n\nSOURCE_PLAN_PATH: %s\n' "$PLAN" >> "$PROMPT_PATH"
printf 'SOURCE_PLAN_START\n' >> "$PROMPT_PATH"
cat "$PLAN" >> "$PROMPT_PATH"
printf '\nSOURCE_PLAN_END\n' >> "$PROMPT_PATH"

CMD=(
  codex exec
  --skip-git-repo-check
  --ephemeral
  -C "$TARGET"
  --output-last-message "$RAW_OUTPUT"
)
if [[ -n "$MODEL" ]]; then
  CMD+=(--model "$MODEL")
fi

if ! "${CMD[@]}" - < "$PROMPT_PATH" >"$LOG_PATH" 2>&1; then
  echo "[error] codex failed while normalizing plan. See log: $LOG_PATH" >&2
  exit 1
fi

python3 - "$RAW_OUTPUT" "$OUT" <<'PY'
import re
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
if not src:
    raise SystemExit("codex returned empty output")

if src.startswith("```"):
    lines = src.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    src = "\n".join(lines).strip()

required_sections = [
    "# Normalized Research Plan",
    "## Objectives",
    "## Constraints",
    "## Environment and Resources",
    "## Milestones",
    "## Task Checklist",
    "## Evaluation and Success Criteria",
    "## Execution Signals",
    "## Risks and Mitigations",
    "## Open Questions",
    "## Source Mapping",
]

lines = [line.strip() for line in src.splitlines()]
pos = 0
for section in required_sections:
    try:
        idx = lines.index(section, pos)
    except ValueError as exc:
        raise SystemExit(f"normalized plan missing section: {section}") from exc
    pos = idx + 1

if not re.search(r"(?m)^\s*-\s*\[\s\]\s+.+$", src):
    raise SystemExit("normalized plan has no checkbox items under task checklist")

allowed_signals = {"slurm", "wandb", "huggingface", "webdataset", "evaluation", "inference"}
lines_raw = src.splitlines()
start = None
end = len(lines_raw)
for i, line in enumerate(lines_raw):
    if line.strip() == "## Execution Signals":
        start = i + 1
        break
if start is None:
    raise SystemExit("normalized plan missing execution signals section")
for j in range(start, len(lines_raw)):
    if lines_raw[j].strip().startswith("## "):
        end = j
        break
signal_lines = [ln.strip() for ln in lines_raw[start:end] if ln.strip()]
if not signal_lines:
    raise SystemExit("execution signals section is empty")

if len(signal_lines) == 1 and signal_lines[0].lower() == "- none":
    pass
else:
    for ln in signal_lines:
        m = re.match(r"^- ([a-zA-Z0-9_]+)\s*:\s*.+$", ln)
        if not m:
            raise SystemExit(f"invalid execution signal line: {ln}")
        signal = m.group(1).lower()
        if signal not in allowed_signals:
            raise SystemExit(f"unknown execution signal: {signal}")

Path(sys.argv[2]).write_text(src + "\n", encoding="utf-8")
PY

GENERATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
cat > "$REPORT" <<EOF
# Plan Alignment Report (Generated)

- Generated at (UTC): \`$GENERATED_AT\`
- Source plan: \`$PLAN\`
- Normalized plan: \`$OUT\`
- Codex log: \`$LOG_PATH\`

## Status

- Normalization and structure validation: PASS
- Next step: use normalized plan as input for harness extraction/bootstrap
EOF

echo "[codex-plan] normalized plan: $OUT"
echo "[codex-plan] alignment report: $REPORT"
echo "[codex-plan] log: $LOG_PATH"
