# File Manifest Policy

## Purpose

Translate an uploaded research plan into a Codex-generated file manifest and scaffold bundle for the Codex DL long-running harness.

## Core Files (always generated)

- `.codex-research/research_spec.md`
- `.codex-research/feature_list.json`
- `.codex-research/task_plan.json`
- `.codex-research/required_files.json`
- `.codex-research/session_progress.md`
- `.codex-research/decision_log.md`
- `.codex-research/run_registry.jsonl`
- `.codex-research/init.sh`
- `.codex-research/checks/smoke_test.sh`
- `.codex-research/prompts/initializer.md`
- `.codex-research/prompts/worker.md`
- `.codex-research/workflow/CODEX.md`
- `.codex-research/run_one_task.sh`
- `.codex-research/run_plan.sh`
- `.codex-research/MECHANISM.md`

## Optional Files

- Additional files (for metrics, environment setup, Slurm, tracking, data pipelines, inference) are decided by Codex from full plan context.
- Optional files must still be generated under `.codex-research/` and listed in `required_files.json`.

## Operating Constraints

- Preserve existing files unless `--force` is used.
- Keep generated file paths stable for repeatable sessions.
- Keep `feature_list.json` as the session completion gate.
- Keep `task_plan.json` as the task-level execution gate for automation scripts.
- Do not reduce generation to keyword-only rules for advanced planning fields (metrics, runtime environment, scheduler workflow, validation protocol).
