#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------
# run_codex_exec_loop.sh
#
# Usage:
#   ./scripts/run_codex_exec_loop.sh <N> [-- extra codex exec args...]
#
# Examples:
#   ./scripts/run_codex_exec_loop.sh 1
#
#   REPO_ROOT=/scratch/ts1v23/workspace/vibe_coding/codex_auto_demo \
#   CODEX_BIN=codex \
#   CODEX_PERMISSION_FLAGS="--ask-for-approval never" \
#   SLEEP_BETWEEN_RUNS=300 \
#   ./scripts/run_codex_exec_loop.sh 5 -- --model gpt-5-codex
#
# Notes:
# - Each iteration calls: codex exec "<prompt>"
# - Logs are written to .codex-research/logs/
# - If any run fails (non-zero exit), the script stops immediately.
# - Prompt is designed for one-task-per-run deterministic execution.
# - For Slurm-backed tasks, the prompt instructs Codex to do a single
#   status check and stop instead of busy-waiting.
# --------------------------------------------

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <N> [-- extra codex exec args...]"
  exit 2
fi

N="$1"
shift || true

EXTRA_ARGS=()
if [[ $# -gt 0 ]]; then
  if [[ "${1:-}" == "--" ]]; then
    shift
  fi
  EXTRA_ARGS=("$@")
fi

if ! [[ "$N" =~ ^[0-9]+$ ]] || [[ "$N" -le 0 ]]; then
  echo "Error: N must be a positive integer, got: $N"
  exit 2
fi

CODEX_BIN="${CODEX_BIN:-codex}"
REPO_ROOT="${REPO_ROOT:-$(pwd)}"
SLEEP_BETWEEN_RUNS="${SLEEP_BETWEEN_RUNS:-0}"
CODEX_PERMISSION_FLAGS="${CODEX_PERMISSION_FLAGS:---ask-for-approval never}"
PERMISSION_ARGS=()
if [[ -n "${CODEX_PERMISSION_FLAGS// }" ]]; then
  read -r -a PERMISSION_ARGS <<< "$CODEX_PERMISSION_FLAGS"
fi

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "Error: REPO_ROOT does not exist: $REPO_ROOT"
  exit 2
fi

cd "$REPO_ROOT"

required_paths=(
  ".codex-research"
  ".codex-research/workflow/CODEX.md"
  ".codex-research/session_progress.md"
  ".codex-research/decision_log.md"
  ".codex-research/task_plan.json"
  ".codex-research/feature_list.json"
)
for p in "${required_paths[@]}"; do
  if [[ ! -e "$p" ]]; then
    echo "Error: required path missing: $REPO_ROOT/$p"
    exit 2
  fi
done

LOG_DIR=".codex-research/logs"
mkdir -p "$LOG_DIR"

BATCH_ID="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="$LOG_DIR/batch_${BATCH_ID}.log"

BASE_PROMPT=$(
  cat <<'PROMPT_EOF'
You are a deterministic implementation agent for project <__REPO_ROOT__>.

Read and follow in this exact order:
1) .codex-research/workflow/CODEX.md
2) .codex-research/session_progress.md
3) .codex-research/decision_log.md
4) .codex-research/task_plan.json
5) .codex-research/feature_list.json

Current run_id: __RUN_ID__.
Current UTC time: __RUN_UTC__.

Core execution contract:
- `task_plan.json` is the execution source of truth.
- `feature_list.json` is a capability map, not the primary task selector.
- Complete exactly one eligible task in this run unless CODEX.md explicitly requires only verification/status-check behavior for the current state.
- Never mark `passes=true` without verification evidence that satisfies the task acceptance criteria.
- Make only minimal, task-scoped edits.

Task selection:
- Choose exactly one eligible task where:
  - `passes=false`
  - all `depends_on` tasks already have `passes=true`
- If multiple tasks are eligible:
  - prefer `critical_path=true`
  - otherwise prefer the earliest task in `task_plan.json`
- Do NOT enforce raw file order if `depends_on` allows a different eligible task.
- Do NOT start a task whose dependencies are not satisfied.

External job / Slurm policy:
- Never busy-wait or perform long polling inside one Codex run.
- If a task depends on an external Slurm job:
  - do at most one quick status inspection in this run
  - if needed, submit via the repository's approved entrypoint (for example `./scripts/submit.sh <job_name>`) as defined in CODEX.md
  - record job id, log path, and next expected check location/time in `.codex-research/session_progress.md`
  - if the external job is still running, stop this run after recording status; do not start a second task
- Do not repeatedly poll logs in a tight loop.

All-tasks-complete behavior:
- Only if `task_plan.json` has no remaining `passes=false` tasks:
  1) inspect `.codex-research/feature_list.json`
  2) if there is concrete, actionable remaining work allowed by CODEX.md, append exactly one new task to `task_plan.json`
  3) any new task must include:
     - id
     - title
     - description
     - milestone
     - feature_refs
     - depends_on
     - blocking_decisions
     - steps
     - artifacts_out
     - acceptance
     - passes=false
  4) if there is no concrete remaining work, record project completion and stop

Repository safety:
- Keep edits scoped to the chosen task.
- Do not make unrelated refactors.
- Do not create side effects outside the repository.
- Do not silently bypass any workflow rule in CODEX.md.
- If you must deviate, record the reason in `.codex-research/decision_log.md`.

Implementation and verification:
- Implement the task end-to-end where feasible.
- Run the verification commands required by the task and CODEX.md.
- Capture evidence snippets, output paths, timestamps, and any generated artifacts.
- If verification is incomplete because an external job is still running, record that explicitly and leave `passes=false`.

Required updates after work:
- `.codex-research/task_plan.json`
- `.codex-research/session_progress.md`
- `.codex-research/decision_log.md`
- `.codex-research/run_registry.jsonl`
- `.codex-research/feature_list.json` if feature state changed
- any source files required for the chosen task

Commit policy:
- Commit only if the chosen task is fully completed and verified.
- Do NOT commit partial, blocked, or failed work.
- Commit message must start with the run_id and include the task id.
- Push after a successful verified commit only if local workflow in CODEX.md allows it.

Failure and blocker handling:
- If blocked by environment/tooling/sandbox issues, record:
  - exact first failing command
  - exact error
  - impacted task id
  - whether any files were modified
- If blocked by an unfinished external Slurm job, record:
  - job id
  - log path
  - current observed status
  - next recommended check
- In any blocked or failed case, do not start another task in this run.

Return exactly one final status summary in this format:

STATUS: <success|blocked_on_external_job|blocked_on_environment|failed_task|project_complete>
TASK_ID: <task id or none>
CHANGED_FILES: <comma-separated paths or none>
VERIFICATION: <verified|not_verified|pending_external_job>
EVIDENCE: <short summary with commands/logs/artifacts>
COMMIT: <hash or none>
NEXT_ACTION: <one sentence>
PROMPT_EOF
)

echo "=== Codex exec batch start ===" | tee -a "$BATCH_LOG"
echo "UTC time: $(date -u '+%F %T')" | tee -a "$BATCH_LOG"
echo "N: $N" | tee -a "$BATCH_LOG"
echo "REPO_ROOT: $REPO_ROOT" | tee -a "$BATCH_LOG"
echo "CODEX_BIN: $CODEX_BIN" | tee -a "$BATCH_LOG"
echo "CODEX_PERMISSION_FLAGS: ${CODEX_PERMISSION_FLAGS:-<empty>}" | tee -a "$BATCH_LOG"
echo "EXTRA_ARGS: ${EXTRA_ARGS[*]:-<none>}" | tee -a "$BATCH_LOG"
echo "SLEEP_BETWEEN_RUNS: $SLEEP_BETWEEN_RUNS" | tee -a "$BATCH_LOG"
echo "Log dir: $LOG_DIR" | tee -a "$BATCH_LOG"
echo "" | tee -a "$BATCH_LOG"

if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
  echo "Error: '$CODEX_BIN' not found in PATH. Set CODEX_BIN or fix PATH." | tee -a "$BATCH_LOG"
  exit 127
fi

extract_status_field() {
  local key="$1"
  local file="$2"
  grep -E "^${key}:" "$file" | tail -n 1 | sed -E "s/^${key}:[[:space:]]*//" || true
}

for i in $(seq 1 "$N"); do
  RUN_TS="$(date -u +%Y%m%dT%H%M%SZ)"
  RUN_UTC="$(date -u '+%F %T')"
  RUN_LOG="$LOG_DIR/run_${BATCH_ID}_${i}_${RUN_TS}.log"

  PROMPT="${BASE_PROMPT//__RUN_ID__/$RUN_TS}"
  PROMPT="${PROMPT//__RUN_UTC__/$RUN_UTC}"
  PROMPT="${PROMPT//__REPO_ROOT__/$REPO_ROOT}"

  echo "---- [${i}/${N}] START ${RUN_TS} ----" | tee -a "$BATCH_LOG" "$RUN_LOG"
  START_EPOCH="$(date +%s)"

  set +e
  "$CODEX_BIN" exec \
    -C "$REPO_ROOT" \
    "${PERMISSION_ARGS[@]}" \
    "${EXTRA_ARGS[@]}" \
    "$PROMPT" \
    > >(tee -a "$RUN_LOG") 2> >(tee -a "$RUN_LOG" >&2)
  EXIT_CODE=$?
  set -e

  END_EPOCH="$(date +%s)"
  ELAPSED="$((END_EPOCH - START_EPOCH))"

  if [[ "$EXIT_CODE" -ne 0 ]]; then
    echo "---- [${i}/${N}] FAIL exit_code=${EXIT_CODE} elapsed=${ELAPSED}s ----" | tee -a "$BATCH_LOG" "$RUN_LOG"
    echo "Run log: $RUN_LOG" | tee -a "$BATCH_LOG"
    echo "Stopping batch due to codex exec failure." | tee -a "$BATCH_LOG"
    exit "$EXIT_CODE"
  fi

  STATUS="$(extract_status_field "STATUS" "$RUN_LOG")"
  TASK_ID="$(extract_status_field "TASK_ID" "$RUN_LOG")"
  VERIFICATION="$(extract_status_field "VERIFICATION" "$RUN_LOG")"
  COMMIT_HASH="$(extract_status_field "COMMIT" "$RUN_LOG")"
  NEXT_ACTION="$(extract_status_field "NEXT_ACTION" "$RUN_LOG")"

  echo "Parsed STATUS: ${STATUS:-<missing>}" | tee -a "$BATCH_LOG" "$RUN_LOG"
  echo "Parsed TASK_ID: ${TASK_ID:-<missing>}" | tee -a "$BATCH_LOG" "$RUN_LOG"
  echo "Parsed VERIFICATION: ${VERIFICATION:-<missing>}" | tee -a "$BATCH_LOG" "$RUN_LOG"
  echo "Parsed COMMIT: ${COMMIT_HASH:-<missing>}" | tee -a "$BATCH_LOG" "$RUN_LOG"
  echo "Parsed NEXT_ACTION: ${NEXT_ACTION:-<missing>}" | tee -a "$BATCH_LOG" "$RUN_LOG"

  if [[ -z "${STATUS:-}" ]]; then
    echo "---- [${i}/${N}] FAIL missing STATUS line elapsed=${ELAPSED}s ----" | tee -a "$BATCH_LOG" "$RUN_LOG"
    echo "Run log: $RUN_LOG" | tee -a "$BATCH_LOG"
    echo "Stopping batch because structured summary was not returned." | tee -a "$BATCH_LOG"
    exit 3
  fi

  echo "---- [${i}/${N}] OK exit_code=0 elapsed=${ELAPSED}s status=${STATUS} ----" | tee -a "$BATCH_LOG" "$RUN_LOG"
  echo "Run log: $RUN_LOG" | tee -a "$BATCH_LOG"

  case "$STATUS" in
    success)
      ;;
    blocked_on_external_job)
      echo "Stopping batch because task is waiting on external Slurm job." | tee -a "$BATCH_LOG"
      exit 0
      ;;
    blocked_on_environment|failed_task)
      echo "Stopping batch because STATUS=${STATUS}." | tee -a "$BATCH_LOG"
      exit 4
      ;;
    project_complete)
      echo "Stopping batch because project is complete." | tee -a "$BATCH_LOG"
      exit 0
      ;;
    *)
      echo "Stopping batch because STATUS is unrecognized: $STATUS" | tee -a "$BATCH_LOG"
      exit 5
      ;;
  esac

  echo "" | tee -a "$BATCH_LOG"

  if [[ "$i" -lt "$N" && "$SLEEP_BETWEEN_RUNS" -gt 0 ]]; then
    echo "Sleeping ${SLEEP_BETWEEN_RUNS}s before next run..." | tee -a "$BATCH_LOG"
    sleep "$SLEEP_BETWEEN_RUNS"
  fi
done

echo "=== Codex exec batch done ===" | tee -a "$BATCH_LOG"
echo "UTC time: $(date -u '+%F %T')" | tee -a "$BATCH_LOG"
echo "Batch log: $BATCH_LOG" | tee -a "$BATCH_LOG"
