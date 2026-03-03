#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_SCRIPT="$SCRIPT_DIR/codex_research_harness.py"
NORMALIZE_SCRIPT="$SCRIPT_DIR/normalize_plan_with_codex.sh"

MODE="all"
PLAN=""
TARGET=""
OUT=""
FORCE=0
CODEX_PLAN_STAGE="required"  # required|auto|off
CODEX_MODEL=""

usage() {
  cat <<'USAGE'
Usage:
  prepare_from_plan.sh --plan PLAN_FILE --target TARGET_DIR [--mode MODE] [--out OUTPUT_FILE] [--force]
                       [--codex-plan-stage STAGE] [--codex-model MODEL] [--skip-codex-alignment]

Required:
  --plan      Uploaded plan file path
  --target    Target output directory

Modes:
  all         Extract + bootstrap + gen-doc (default)
  extract     Only generate required_files manifest
  bootstrap   Only generate scaffold files
  gen-doc     Only regenerate MECHANISM.md

Codex plan stage:
  required    Must normalize the plan with Codex before framework generation (default)
  auto        Try Codex normalization; fallback to original plan if it fails
  off         Skip Codex normalization and use original plan directly
USAGE
}

invoke_framework() {
  local active_plan="$1"
  local target_root="$2"

  case "$MODE" in
    extract)
      if [[ -z "$OUT" ]]; then
        OUT="$target_root/.codex-research/required_files.generated.json"
      fi
      mkdir -p "$(dirname "$OUT")"
      python3 "$FRAMEWORK_SCRIPT" extract --plan "$active_plan" --out "$OUT"
      ;;
    bootstrap)
      if [[ "$FORCE" -eq 1 ]]; then
        python3 "$FRAMEWORK_SCRIPT" bootstrap --plan "$active_plan" --target "$target_root" --force
      else
        python3 "$FRAMEWORK_SCRIPT" bootstrap --plan "$active_plan" --target "$target_root"
      fi
      ;;
    gen-doc)
      python3 "$FRAMEWORK_SCRIPT" gen-doc --plan "$active_plan" --target "$target_root"
      ;;
    all)
      if [[ "$FORCE" -eq 1 ]]; then
        python3 "$FRAMEWORK_SCRIPT" all --plan "$active_plan" --target "$target_root" --force
      else
        python3 "$FRAMEWORK_SCRIPT" all --plan "$active_plan" --target "$target_root"
      fi
      ;;
    *)
      echo "[error] unsupported --mode: $MODE (expected: extract|bootstrap|gen-doc|all)" >&2
      return 1
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
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
    --force)
      FORCE=1
      shift
      ;;
    --codex-plan-stage)
      CODEX_PLAN_STAGE="$2"
      shift 2
      ;;
    --codex-model)
      CODEX_MODEL="$2"
      shift 2
      ;;
    --skip-codex-alignment)
      CODEX_PLAN_STAGE="off"
      shift
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
  echo "[error] missing required --plan (please provide uploaded plan path)" >&2
  usage >&2
  exit 1
fi

if [[ -z "$TARGET" ]]; then
  echo "[error] missing required --target (please provide target output directory)" >&2
  usage >&2
  exit 1
fi

if [[ ! -f "$PLAN" ]]; then
  echo "[error] plan file does not exist: $PLAN" >&2
  exit 1
fi

if [[ ! -f "$FRAMEWORK_SCRIPT" ]]; then
  echo "[error] local framework script not found: $FRAMEWORK_SCRIPT" >&2
  exit 1
fi

PLAN="$(cd "$(dirname "$PLAN")" && pwd)/$(basename "$PLAN")"
mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

case "$CODEX_PLAN_STAGE" in
  required|auto|off)
    ;;
  *)
    echo "[error] invalid --codex-plan-stage: $CODEX_PLAN_STAGE (expected: required|auto|off)" >&2
    exit 1
    ;;
esac

ACTIVE_PLAN="$PLAN"
NORMALIZED_PLAN="$TARGET/.codex-research/plan/normalized_plan.md"
ALIGNMENT_REPORT="$TARGET/.codex-research/plan/alignment_report.md"

if [[ "$CODEX_PLAN_STAGE" != "off" ]]; then
  if [[ ! -x "$NORMALIZE_SCRIPT" ]]; then
    echo "[error] normalize script is missing or not executable: $NORMALIZE_SCRIPT" >&2
    exit 1
  fi

  normalize_args=(
    --plan "$PLAN"
    --target "$TARGET"
    --out "$NORMALIZED_PLAN"
    --report "$ALIGNMENT_REPORT"
  )
  if [[ -n "$CODEX_MODEL" ]]; then
    normalize_args+=(--model "$CODEX_MODEL")
  fi

  set +e
  bash "$NORMALIZE_SCRIPT" "${normalize_args[@]}"
  normalize_status=$?
  set -e

  if [[ "$normalize_status" -eq 0 ]]; then
    ACTIVE_PLAN="$NORMALIZED_PLAN"
  elif [[ "$CODEX_PLAN_STAGE" == "required" ]]; then
    echo "[error] codex plan alignment failed and stage is required" >&2
    exit 1
  else
    echo "[warn] codex plan alignment failed; fallback to original plan: $PLAN" >&2
  fi
fi

invoke_framework "$ACTIVE_PLAN" "$TARGET"

echo "[ok] mode=$MODE source_plan=$PLAN active_plan=$ACTIVE_PLAN target=$TARGET codex_plan_stage=$CODEX_PLAN_STAGE"

if [[ "$MODE" == "all" || "$MODE" == "bootstrap" ]]; then
  echo "[next] run one task: bash \"$TARGET/.codex-research/run_one_task.sh\" --target \"$TARGET\""
  echo "[next] run N tasks: bash \"$TARGET/.codex-research/run_plan.sh\" 5 --target \"$TARGET\""
fi
