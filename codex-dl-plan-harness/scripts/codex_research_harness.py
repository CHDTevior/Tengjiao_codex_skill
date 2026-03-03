#!/usr/bin/env python3
"""Codex long-running harness for personal deep-learning research projects.

This script reads a user plan file, derives the required harness files,
bootstraps a deterministic project scaffold, and can generate a mechanism
introduction markdown document inside the target project.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple


CORE_REQUIRED_FILES = [
    {
        "path": ".codex-research/research_spec.md",
        "template": "research_spec",
        "reason": "Single source of truth for research goals and constraints.",
    },
    {
        "path": ".codex-research/feature_list.json",
        "template": "feature_list",
        "reason": "Session-to-session acceptance checklist.",
    },
    {
        "path": ".codex-research/task_plan.json",
        "template": "task_plan",
        "reason": "Task-driven execution plan used by Codex run scripts.",
    },
    {
        "path": ".codex-research/required_files.json",
        "template": "required_files",
        "reason": "Machine-readable manifest generated from the uploaded plan.",
    },
    {
        "path": ".codex-research/session_progress.md",
        "template": "session_progress",
        "reason": "Human-readable handoff log between sessions.",
    },
    {
        "path": ".codex-research/decision_log.md",
        "template": "decision_log",
        "reason": "Captures major design decisions and why they were made.",
    },
    {
        "path": ".codex-research/run_registry.jsonl",
        "template": "run_registry",
        "reason": "Append-only run registry for reproducibility.",
    },
    {
        "path": ".codex-research/init.sh",
        "template": "init_sh",
        "reason": "Deterministic environment startup command for each new session.",
    },
    {
        "path": ".codex-research/checks/smoke_test.sh",
        "template": "smoke_test",
        "reason": "Fail-fast preflight test before any new coding work.",
    },
    {
        "path": ".codex-research/prompts/initializer.md",
        "template": "initializer_prompt",
        "reason": "First-session operating procedure for Codex.",
    },
    {
        "path": ".codex-research/prompts/worker.md",
        "template": "worker_prompt",
        "reason": "Subsequent-session operating procedure for Codex.",
    },
    {
        "path": ".codex-research/workflow/CODEX.md",
        "template": "codex_workflow",
        "reason": "Step-by-step workflow for one-task-per-session execution.",
    },
    {
        "path": ".codex-research/run_one_task.sh",
        "template": "run_one_task",
        "reason": "Execute exactly one pending task from task_plan.json via codex exec.",
    },
    {
        "path": ".codex-research/run_plan.sh",
        "template": "run_plan",
        "reason": "Loop run_one_task.sh for N iterations with task-progress checks.",
    },
    {
        "path": ".codex-research/MECHANISM.md",
        "template": "mechanism",
        "reason": "In-project mechanism introduction document.",
    },
]

OPTIONAL_FILE_RULES = [
    {
        "signal": "uses_slurm",
        "path": ".codex-research/slurm/train.sbatch",
        "template": "slurm_train",
        "reason": "Plan mentions Slurm or HPC scheduling.",
    },
    {
        "signal": "uses_slurm",
        "path": ".codex-research/slurm/debug.sbatch",
        "template": "slurm_debug",
        "reason": "Plan mentions Slurm/HPC debug workflow.",
    },
    {
        "signal": "uses_wandb",
        "path": ".codex-research/config/wandb.yaml",
        "template": "wandb_config",
        "reason": "Plan mentions W&B tracking.",
    },
    {
        "signal": "uses_hf",
        "path": ".codex-research/config/hf_dataset.yaml",
        "template": "hf_dataset_config",
        "reason": "Plan mentions HuggingFace dataset workflows.",
    },
    {
        "signal": "uses_webdataset",
        "path": ".codex-research/config/webdataset.yaml",
        "template": "webdataset_config",
        "reason": "Plan mentions WebDataset or shard streaming.",
    },
    {
        "signal": "needs_eval",
        "path": ".codex-research/config/eval.yaml",
        "template": "eval_config",
        "reason": "Plan contains evaluation, metrics, or benchmark terms.",
    },
    {
        "signal": "needs_inference",
        "path": ".codex-research/config/inference.yaml",
        "template": "inference_config",
        "reason": "Plan mentions inference, deployment, or serving.",
    },
]

SIGNAL_KEYWORDS = {
    "uses_slurm": ["slurm", "sbatch", "srun", "h100", "a100", "hpc"],
    "uses_wandb": ["wandb", "weights & biases", "weights and biases"],
    "uses_hf": ["huggingface", "hf dataset", "datasets.load_dataset"],
    "uses_webdataset": ["webdataset", ".tar shards", "shard"],
    "needs_eval": [
        "eval",
        "evaluation",
        "metric",
        "benchmark",
        "fid",
        "fvd",
        "lpips",
        "ablation",
    ],
    "needs_inference": ["inference", "serving", "deployment", "demo", "gradio"],
}

TASK_LINE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+(?:\[[ xX]\]\s*)?(.+?)\s*$")
HEADING_LINE = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def detect_signals(plan_text: str) -> Dict[str, bool]:
    lowered = plan_text.lower()
    signals = {}
    for key, words in SIGNAL_KEYWORDS.items():
        signals[key] = any(word in lowered for word in words)
    return signals


def collect_headings(plan_text: str) -> List[str]:
    headings: List[str] = []
    for line in plan_text.splitlines():
        match = HEADING_LINE.match(line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def collect_tasks(plan_text: str, max_items: int = 80) -> List[str]:
    tasks: List[str] = []
    for line in plan_text.splitlines():
        match = TASK_LINE.match(line)
        if match:
            item = match.group(1).strip()
            if item and item not in tasks:
                tasks.append(item)
        if len(tasks) >= max_items:
            break
    return tasks


def build_required_files(signals: Dict[str, bool]) -> List[Dict[str, str]]:
    result = [dict(item) for item in CORE_REQUIRED_FILES]
    for rule in OPTIONAL_FILE_RULES:
        if signals.get(rule["signal"], False):
            result.append(
                {
                    "path": rule["path"],
                    "template": rule["template"],
                    "reason": rule["reason"],
                }
            )
    return result


def build_feature_list(tasks: List[str], signals: Dict[str, bool]) -> List[Dict[str, object]]:
    baseline = [
        "Environment bootstrap script works on a clean session.",
        "Smoke tests run before training changes.",
        "One-session-one-feature discipline is followed.",
    ]
    if signals.get("needs_eval"):
        baseline.append("Evaluation metrics config is executable end-to-end.")
    if signals.get("uses_slurm"):
        baseline.append("Slurm training submission template works in dry-run mode.")

    merged: List[str] = []
    for item in baseline + tasks:
        normalized = item.strip()
        if normalized and normalized not in merged:
            merged.append(normalized)

    records = []
    for index, description in enumerate(merged[:200], start=1):
        feature_id = f"F-{index:04d}"
        records.append(
            {
                "id": feature_id,
                "category": "research",
                "description": description,
                "steps": [
                    "Reproduce baseline behavior before modification.",
                    "Implement the minimal change for this feature only.",
                    "Run smoke/eval checks and attach evidence.",
                ],
                "passes": False,
            }
        )
    return records


def to_task_title(text: str, max_len: int = 80) -> str:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return "Untitled task"
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 3].rstrip() + "..."


def build_task_plan(
    tasks: List[str],
    headings: List[str],
    signals: Dict[str, bool],
    plan_path: str,
    generated_at: str,
) -> Dict[str, object]:
    ordered_candidates: List[str] = []
    for item in tasks:
        normalized = " ".join(item.strip().split())
        if normalized and normalized not in ordered_candidates:
            ordered_candidates.append(normalized)

    if not ordered_candidates:
        for heading in headings[:30]:
            candidate = f"Implement plan section: {heading}"
            if candidate not in ordered_candidates:
                ordered_candidates.append(candidate)

    if not ordered_candidates:
        ordered_candidates = [
            "Bootstrap project scaffold and verify base environment.",
            "Implement the first research milestone from research_spec.md.",
        ]

    records: List[Dict[str, object]] = []
    for index, description in enumerate(ordered_candidates[:200], start=1):
        task_id = f"T-{index:04d}"
        steps = [
            "Read .codex-research/research_spec.md and identify the minimal required change.",
            "Implement this task only and avoid unrelated refactors.",
            "Run .codex-research/checks/smoke_test.sh and task-specific validation commands.",
            "Record evidence in .codex-research/session_progress.md and run_registry.jsonl.",
        ]
        if signals.get("needs_eval"):
            steps.append("When applicable, run eval dry-run and capture metric command evidence.")
        records.append(
            {
                "id": task_id,
                "title": to_task_title(description),
                "description": description,
                "steps": steps,
                "passes": False,
            }
        )

    return {
        "project": Path(plan_path).stem,
        "generated_at": generated_at,
        "plan_path": plan_path,
        "rules": [
            "Exactly one task per session.",
            "Do not set passes=true without command/test evidence.",
            "If blocked, keep passes=false and document blocker clearly.",
        ],
        "tasks": records,
    }


def as_json_pretty(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def render_template(
    template_name: str,
    ctx: Dict[str, object],
) -> str:
    plan_path = str(ctx["plan_path"])
    now = str(ctx["generated_at"])
    headings = ctx.get("headings", [])
    tasks = ctx.get("tasks", [])
    required_files = ctx.get("required_files", [])
    signals = ctx.get("signals", {})

    if template_name == "research_spec":
        heading_lines = "\n".join(f"- {h}" for h in headings[:20]) or "- (No markdown headings detected)"
        task_lines = "\n".join(f"- {t}" for t in tasks[:30]) or "- (No explicit checklist/task lines detected)"
        return f"""# Research Spec (Generated)

- Source plan: `{plan_path}`
- Generated at (UTC): `{now}`

## Plan Headings
{heading_lines}

## Extracted Tasks
{task_lines}

## Non-Negotiable Rules
- Keep one session focused on one task from `task_plan.json`.
- Run `checks/smoke_test.sh` before and after each task implementation.
- Update `session_progress.md` and append to `run_registry.jsonl` at session end.
- Do not mark a task as `passes=true` without test evidence.
"""

    if template_name == "required_files":
        payload = {
            "generated_at": now,
            "plan_path": plan_path,
            "signals": signals,
            "required_files": required_files,
        }
        return as_json_pretty(payload)

    if template_name == "feature_list":
        return as_json_pretty(ctx["feature_list"])

    if template_name == "task_plan":
        return as_json_pretty(ctx["task_plan"])

    if template_name == "session_progress":
        return """# Session Progress

| Session | Date (UTC) | Focus Task | Result | Evidence | Next Step |
| --- | --- | --- | --- | --- | --- |
"""

    if template_name == "decision_log":
        return """# Decision Log

| Date (UTC) | Decision | Reason | Reversal Condition |
| --- | --- | --- | --- |
"""

    if template_name == "run_registry":
        return ""

    if template_name == "init_sh":
        return """#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[init] project root: $ROOT_DIR"
if [ -f requirements.txt ]; then
  echo "[init] requirements.txt detected"
  echo "[init] run: pip install -r requirements.txt"
fi
if [ -f pyproject.toml ]; then
  echo "[init] pyproject.toml detected"
  echo "[init] run: pip install -e ."
fi

echo "[init] Next step: bash .codex-research/checks/smoke_test.sh"
"""

    if template_name == "smoke_test":
        return """#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[smoke] cwd=$(pwd)"
python3 - <<'PY'
import json
from pathlib import Path

feature_list = Path('.codex-research/feature_list.json')
if not feature_list.exists():
    raise SystemExit('feature_list.json is missing')

feature_data = json.loads(feature_list.read_text(encoding='utf-8'))
if not isinstance(feature_data, list):
    raise SystemExit('feature_list.json must be a list')
task_plan = Path('.codex-research/task_plan.json')
if not task_plan.exists():
    raise SystemExit('task_plan.json is missing')

task_data = json.loads(task_plan.read_text(encoding='utf-8'))
tasks = task_data.get('tasks')
if not isinstance(tasks, list):
    raise SystemExit('task_plan.json must contain top-level "tasks" list')

print(f'[smoke] feature count={len(feature_data)}')
print(f'[smoke] task count={len(tasks)}')
PY

echo "[smoke] PASS"
"""

    if template_name == "initializer_prompt":
        return """# Initializer Prompt (DL Research Edition)

1. Read `.codex-research/research_spec.md` and `.codex-research/required_files.json`.
2. Validate that all listed required files exist. Create missing files only; do not alter existing semantics.
3. Ensure `.codex-research/task_plan.json` contains executable one-task records with `passes=false` by default.
4. Run `.codex-research/checks/smoke_test.sh` and record output in `.codex-research/session_progress.md`.
5. End this session in a clean handoff state.
"""

    if template_name == "worker_prompt":
        return """# Worker Prompt (DL Research Edition)

For each session:
1. Run `pwd`, then `bash .codex-research/checks/smoke_test.sh`.
2. Read `.codex-research/task_plan.json`, pick exactly one `passes=false` task.
3. Implement the minimal code/config change for that item only.
4. Run the relevant tests or training dry-run (and eval if applicable).
5. Set only that task to `passes=true` when evidence exists.
6. Append a concise entry to `.codex-research/session_progress.md` and `.codex-research/run_registry.jsonl`.
7. Stop with a clean, reproducible state for the next session.
"""

    if template_name == "codex_workflow":
        return """# Codex Workflow (Task-Driven Harness)

Every coding session must follow this order:

1. Initialize environment:
   - Run `bash .codex-research/init.sh`
2. Select exactly one pending task:
   - Read `.codex-research/task_plan.json`
   - Pick the first task with `passes: false`
3. Implement only that task:
   - Follow task description and step list
   - Avoid unrelated refactors
4. Validate:
   - Run `bash .codex-research/checks/smoke_test.sh` before and after changes
   - Run task-specific tests, dry-runs, or eval commands
5. Update state:
   - Update `.codex-research/session_progress.md`
   - Append one JSON line to `.codex-research/run_registry.jsonl`
   - Flip only the selected task to `passes: true` when evidence exists
6. Stop:
   - End session with a clean handoff for the next run

Blocking rule:
- If blocked by missing credentials/resources/external system, keep `passes: false`,
  write blocker details in `session_progress.md`, and stop without pretending completion.
"""

    if template_name == "run_one_task":
        return """#!/usr/bin/env bash
set -euo pipefail

TARGET=""
MODEL="${CODEX_MODEL:-}"
SKIP_INIT=0

usage() {
  cat <<'EOF'
Usage:
  run_one_task.sh [--target TARGET_DIR] [--model MODEL] [--skip-init]

Description:
  Execute exactly one pending task from .codex-research/task_plan.json with codex exec.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target|--project-root)
      TARGET="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --skip-init)
      SKIP_INIT=1
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

if [[ -z "$TARGET" ]]; then
  TARGET="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
TARGET="$(cd "$TARGET" && pwd)"

if ! command -v codex >/dev/null 2>&1; then
  echo "[error] codex CLI is not available in PATH" >&2
  exit 1
fi

TASK_FILE="$TARGET/.codex-research/task_plan.json"
WORKFLOW_FILE="$TARGET/.codex-research/workflow/CODEX.md"
PROGRESS_FILE="$TARGET/.codex-research/session_progress.md"
REGISTRY_FILE="$TARGET/.codex-research/run_registry.jsonl"
LOG_DIR="$TARGET/.codex-research/automation-logs"

for path in "$TASK_FILE" "$WORKFLOW_FILE" "$PROGRESS_FILE" "$REGISTRY_FILE"; do
  if [[ ! -f "$path" ]]; then
    echo "[error] required file not found: $path" >&2
    exit 1
  fi
done

mkdir -p "$LOG_DIR"

if [[ "$SKIP_INIT" -eq 0 ]]; then
  INIT_SCRIPT="$TARGET/.codex-research/init.sh"
  if [[ -x "$INIT_SCRIPT" ]]; then
    echo "[run-one] running init script"
    (cd "$TARGET" && bash .codex-research/init.sh)
  else
    echo "[run-one] init script missing or not executable, skipping"
  fi
fi

NEXT_TASK_JSON="$(python3 - "$TASK_FILE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
tasks = payload.get("tasks")
if not isinstance(tasks, list):
    raise SystemExit("task_plan.json must contain top-level 'tasks' list")

for task in tasks:
    if isinstance(task, dict) and task.get("passes") is False:
        print(json.dumps(task, ensure_ascii=False))
        raise SystemExit(0)

print("{}")
PY
)"

if [[ "$NEXT_TASK_JSON" == "{}" ]]; then
  echo "[run-one] no pending tasks left"
  exit 0
fi

TASK_ID="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("id",""))' <<<"$NEXT_TASK_JSON")"
TASK_TITLE="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("title",""))' <<<"$NEXT_TASK_JSON")"
TASK_DESC="$(python3 -c 'import json,sys; print(json.loads(sys.stdin.read()).get("description",""))' <<<"$NEXT_TASK_JSON")"

if [[ -z "$TASK_ID" ]]; then
  echo "[error] selected task is missing id" >&2
  exit 1
fi

PROMPT_FILE="$(mktemp)"
trap 'rm -f "$PROMPT_FILE"' EXIT

cat > "$PROMPT_FILE" <<EOF
You are running one step in a Codex long-running harness.

Read and follow:
- .codex-research/workflow/CODEX.md

Target task for this session (only this one):
- id: $TASK_ID
- title: $TASK_TITLE
- description: $TASK_DESC

Hard requirements:
1. Run .codex-research/checks/smoke_test.sh before and after implementation.
2. Work only on task id $TASK_ID.
3. Update .codex-research/session_progress.md with what changed and test evidence.
4. Append one JSON line to .codex-research/run_registry.jsonl.
5. In .codex-research/task_plan.json, set passes=true only for task id $TASK_ID and only when evidence exists.
6. Stop after this single task or when blocked.

If blocked, keep passes=false and write blocker details in session_progress.md.
EOF

RUN_TS="$(date -u +%Y%m%d_%H%M%S)"
RUN_LOG="$LOG_DIR/run-one-$RUN_TS.log"

CMD=(
  codex exec
  --skip-git-repo-check
  --sandbox workspace-write
  -C "$TARGET"
)
if [[ -n "$MODEL" ]]; then
  CMD+=(--model "$MODEL")
fi

echo "[run-one] task_id=$TASK_ID"
echo "[run-one] log=$RUN_LOG"

if "${CMD[@]}" - < "$PROMPT_FILE" 2>&1 | tee "$RUN_LOG"; then
  echo "[run-one] completed"
else
  rc=$?
  echo "[run-one] codex exited with status=$rc" >&2
  exit "$rc"
fi
"""

    if template_name == "run_plan":
        return """#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: run_plan.sh <runs> [--target TARGET_DIR] [--model MODEL] [--skip-init]"
}

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  usage
  exit 0
fi

RUNS="$1"
shift

if ! [[ "$RUNS" =~ ^[0-9]+$ ]] || [[ "$RUNS" -lt 1 ]]; then
  echo "[error] runs must be a positive integer" >&2
  exit 1
fi

TARGET=""
MODEL="${CODEX_MODEL:-}"
SKIP_INIT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --target|--project-root)
      TARGET="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --skip-init)
      SKIP_INIT=1
      shift
      ;;
    *)
      echo "[error] unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  TARGET="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
TARGET="$(cd "$TARGET" && pwd)"

RUN_ONE="$TARGET/.codex-research/run_one_task.sh"
TASK_FILE="$TARGET/.codex-research/task_plan.json"

if [[ ! -x "$RUN_ONE" ]]; then
  echo "[error] run_one_task.sh is missing or not executable: $RUN_ONE" >&2
  exit 1
fi
if [[ ! -f "$TASK_FILE" ]]; then
  echo "[error] task_plan.json is missing: $TASK_FILE" >&2
  exit 1
fi

count_remaining() {
  python3 - "$TASK_FILE" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
tasks = payload.get("tasks")
if not isinstance(tasks, list):
    raise SystemExit("task_plan.json must contain top-level 'tasks' list")
print(sum(1 for task in tasks if isinstance(task, dict) and task.get("passes") is False))
PY
}

echo "[run-plan] target=$TARGET"
echo "[run-plan] requested_runs=$RUNS"

for ((run=1; run<=RUNS; run++)); do
  remaining_before="$(count_remaining)"
  if [[ "$remaining_before" -eq 0 ]]; then
    echo "[run-plan] all tasks completed before run $run"
    break
  fi

  echo "[run-plan] run=$run remaining_before=$remaining_before"
  args=(--target "$TARGET")
  if [[ -n "$MODEL" ]]; then
    args+=(--model "$MODEL")
  fi
  if [[ "$SKIP_INIT" -eq 1 ]]; then
    args+=(--skip-init)
  fi

  bash "$RUN_ONE" "${args[@]}"

  remaining_after="$(count_remaining)"
  completed=$((remaining_before - remaining_after))
  echo "[run-plan] run=$run completed_tasks=$completed remaining_after=$remaining_after"

  if [[ "$remaining_after" -eq 0 ]]; then
    echo "[run-plan] all tasks completed"
    break
  fi

  if [[ "$run" -lt "$RUNS" ]]; then
    sleep 2
  fi
done
"""

    if template_name == "slurm_train":
        return """#!/bin/bash
#SBATCH --job-name=codex-dl-train
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x-%j.out

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

bash .codex-research/init.sh
# Replace with your real command:
# srun python train.py --config configs/train.yaml
"""

    if template_name == "slurm_debug":
        return """#!/bin/bash
#SBATCH --job-name=codex-dl-debug
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x-%j.out

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

bash .codex-research/checks/smoke_test.sh
# Replace with your lightweight debug command:
# srun python train.py --config configs/train.yaml trainer.max_steps=10
"""

    if template_name == "wandb_config":
        return """mode: offline
project: codex-dl-research
entity: your_entity
run_name: ${RUN_NAME:-session-local}
"""

    if template_name == "hf_dataset_config":
        return """dataset:
  repo_id: your-org/your-dataset
  split: train
  cache_dir: ~/.cache/huggingface/datasets
"""

    if template_name == "webdataset_config":
        return """webdataset:
  shard_pattern: data/train-{000000..000127}.tar
  shuffle: 1000
  decode: pil
"""

    if template_name == "eval_config":
        return """evaluation:
  primary_metric: fid
  secondary_metrics:
    - lpips
    - ssim
    - vendi
  eval_every_n_steps: 1000
"""

    if template_name == "inference_config":
        return """inference:
  batch_size: 8
  num_workers: 4
  precision: fp16
  save_dir: outputs/inference
"""

    if template_name == "mechanism":
        return build_mechanism_markdown(ctx)

    raise ValueError(f"Unknown template: {template_name}")


def build_mechanism_markdown(ctx: Dict[str, object]) -> str:
    now = str(ctx["generated_at"])
    plan_path = str(ctx["plan_path"])
    signals = ctx.get("signals", {})
    enabled = [k for k, v in signals.items() if v]
    enabled_text = ", ".join(enabled) if enabled else "none"

    return f"""# Codex Long-Running Research Harness Mechanism

- Generated at (UTC): `{now}`
- Source plan: `{plan_path}`
- Detected optional capabilities: `{enabled_text}`

## Why This Mechanism

This harness adapts long-running agent workflows to Codex-based research development:
- External artifacts carry memory across sessions.
- One-session-one-task control prevents context collapse.
- Fail-fast smoke checks prevent dirty handoffs.
- Structured logs preserve reproducibility.

## Session Lifecycle

```mermaid
flowchart TD
    P[Plan File] --> E[Extract Signals and Tasks]
    E --> M[Generate required_files.json + task_plan.json]
    M --> B[Bootstrap .codex-research Files]
    B --> R[run_one_task.sh picks first pending task]
    R --> T[Implement and Validate]
    T --> U[Update task_plan + progress + registry]
    U --> N[Next Session]
```

## Files and Roles

- `.codex-research/research_spec.md`: normalized plan and immutable constraints.
- `.codex-research/task_plan.json`: task queue for step-by-step execution (`passes` is completion gate).
- `.codex-research/feature_list.json`: backward-compatible feature checklist.
- `.codex-research/session_progress.md`: human handoff log.
- `.codex-research/run_registry.jsonl`: machine-readable run history.
- `.codex-research/workflow/CODEX.md`: mandatory operational workflow for each run.
- `.codex-research/run_one_task.sh`: execute one pending task with codex.
- `.codex-research/run_plan.sh`: loop one-task execution for N runs.

## Operating Rules

1. Always run `bash .codex-research/checks/smoke_test.sh` first.
2. Work on exactly one `passes=false` task per session.
3. Do not claim completion without evidence.
4. End every session in clean state with updated handoff files.

## Suggested Commands

```bash
bash scripts/prepare_from_plan.sh --plan <your_uploaded_plan.md> --target <your_project_root>
bash <your_project_root>/.codex-research/run_one_task.sh --target <your_project_root>
bash <your_project_root>/.codex-research/run_plan.sh 5 --target <your_project_root>
```
"""


def write_file(path: Path, content: str, force: bool) -> Tuple[bool, str]:
    if path.exists() and not force:
        return False, "exists"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True, "written"


def chmod_if_shell(path: Path) -> None:
    if path.suffix in {".sh", ".sbatch"}:
        current = path.stat().st_mode
        path.chmod(current | 0o111)


def load_or_build_manifest(plan_path: Path) -> Dict[str, object]:
    plan_text = read_text(plan_path)
    signals = detect_signals(plan_text)
    headings = collect_headings(plan_text)
    tasks = collect_tasks(plan_text)
    required_files = build_required_files(signals)
    feature_list = build_feature_list(tasks, signals)
    generated_at = iso_now()
    resolved_plan_path = str(plan_path.resolve())
    task_plan = build_task_plan(
        tasks=tasks,
        headings=headings,
        signals=signals,
        plan_path=resolved_plan_path,
        generated_at=generated_at,
    )
    return {
        "generated_at": generated_at,
        "plan_path": resolved_plan_path,
        "signals": signals,
        "headings": headings,
        "tasks": tasks,
        "required_files": required_files,
        "feature_list": feature_list,
        "task_plan": task_plan,
    }


def cmd_extract(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).resolve()
    out_path = Path(args.out).resolve()
    manifest = load_or_build_manifest(plan_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        as_json_pretty(
            {
                "generated_at": manifest["generated_at"],
                "plan_path": manifest["plan_path"],
                "signals": manifest["signals"],
                "headings": manifest["headings"],
                "tasks": manifest["tasks"],
                "required_files": manifest["required_files"],
                "task_plan": manifest["task_plan"],
            }
        ),
        encoding="utf-8",
    )
    print(f"[extract] wrote {out_path}")
    return 0


def bootstrap_from_manifest(
    target_root: Path,
    manifest: Dict[str, object],
    force: bool,
) -> Tuple[int, int]:
    required_files = manifest["required_files"]
    created = 0
    skipped = 0

    for item in required_files:
        rel_path = item["path"]
        template = item["template"]
        abs_path = target_root / rel_path
        content = render_template(template, manifest)
        wrote, status = write_file(abs_path, content, force)
        if wrote:
            chmod_if_shell(abs_path)
            created += 1
            print(f"[bootstrap] created {abs_path}")
        else:
            skipped += 1
            print(f"[bootstrap] skipped {abs_path} ({status})")

    required_path = target_root / ".codex-research/required_files.json"
    required_payload = {
        "generated_at": manifest["generated_at"],
        "plan_path": manifest["plan_path"],
        "signals": manifest["signals"],
        "required_files": manifest["required_files"],
    }
    required_path.parent.mkdir(parents=True, exist_ok=True)
    required_path.write_text(as_json_pretty(required_payload), encoding="utf-8")

    feature_path = target_root / ".codex-research/feature_list.json"
    feature_path.write_text(as_json_pretty(manifest["feature_list"]), encoding="utf-8")

    task_plan_path = target_root / ".codex-research/task_plan.json"
    task_plan_path.write_text(as_json_pretty(manifest["task_plan"]), encoding="utf-8")

    return created, skipped


def cmd_bootstrap(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).resolve()
    target_root = Path(args.target).resolve()
    manifest = load_or_build_manifest(plan_path)

    created, skipped = bootstrap_from_manifest(target_root, manifest, args.force)
    print(f"[bootstrap] done: created={created}, skipped={skipped}")
    return 0


def cmd_gen_doc(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).resolve()
    target_root = Path(args.target).resolve()
    manifest = load_or_build_manifest(plan_path)
    mechanism_path = target_root / ".codex-research/MECHANISM.md"
    content = render_template("mechanism", manifest)
    mechanism_path.parent.mkdir(parents=True, exist_ok=True)
    mechanism_path.write_text(content, encoding="utf-8")
    print(f"[doc] wrote {mechanism_path}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).resolve()
    target_root = Path(args.target).resolve()
    manifest = load_or_build_manifest(plan_path)

    extract_path = target_root / ".codex-research/required_files.generated.json"
    extract_path.parent.mkdir(parents=True, exist_ok=True)
    extract_payload = {
        "generated_at": manifest["generated_at"],
        "plan_path": manifest["plan_path"],
        "signals": manifest["signals"],
        "headings": manifest["headings"],
        "tasks": manifest["tasks"],
        "required_files": manifest["required_files"],
        "task_plan": manifest["task_plan"],
    }
    extract_path.write_text(as_json_pretty(extract_payload), encoding="utf-8")

    created, skipped = bootstrap_from_manifest(target_root, manifest, args.force)

    mechanism_path = target_root / ".codex-research/MECHANISM.md"
    mechanism_path.write_text(render_template("mechanism", manifest), encoding="utf-8")

    print(f"[all] wrote manifest: {extract_path}")
    print(f"[all] wrote mechanism: {mechanism_path}")
    print(f"[all] done: created={created}, skipped={skipped}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Codex long-running harness bootstrapper for DL research.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    extract = sub.add_parser("extract", help="Extract required files from a plan file")
    extract.add_argument("--plan", required=True, help="Path to uploaded plan file")
    extract.add_argument("--out", required=True, help="Output JSON path")
    extract.set_defaults(func=cmd_extract)

    bootstrap = sub.add_parser("bootstrap", help="Create harness files in target project")
    bootstrap.add_argument("--plan", required=True, help="Path to uploaded plan file")
    bootstrap.add_argument("--target", required=True, help="Target project root")
    bootstrap.add_argument("--force", action="store_true", help="Overwrite existing files")
    bootstrap.set_defaults(func=cmd_bootstrap)

    gen_doc = sub.add_parser("gen-doc", help="Generate mechanism markdown in project")
    gen_doc.add_argument("--plan", required=True, help="Path to uploaded plan file")
    gen_doc.add_argument("--target", required=True, help="Target project root")
    gen_doc.set_defaults(func=cmd_gen_doc)

    all_cmd = sub.add_parser("all", help="Extract + bootstrap + generate doc")
    all_cmd.add_argument("--plan", required=True, help="Path to uploaded plan file")
    all_cmd.add_argument("--target", required=True, help="Target project root")
    all_cmd.add_argument("--force", action="store_true", help="Overwrite existing files")
    all_cmd.set_defaults(func=cmd_all)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    plan_path = Path(getattr(args, "plan", ""))
    if plan_path and not plan_path.exists():
        raise SystemExit(f"Plan file not found: {plan_path}")

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
