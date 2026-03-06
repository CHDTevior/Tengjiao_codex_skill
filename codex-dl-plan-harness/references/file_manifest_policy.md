# File Manifest Policy

## Purpose

Translate an uploaded research plan into a Codex-generated file manifest and scaffold bundle for the Codex DL long-running harness, while preventing task drift, missing dependencies, ambiguous contracts, incomplete evaluation definitions, and non-executable Slurm guidance.

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
- `.codex-research/execution_guide.zh-CN.md`
- `.codex-research/MECHANISM.md`

## Structured Metadata Contract

- `task_plan.json` is the execution truth source.
- `feature_list.json` is the capability map.
- Task and feature references must be bidirectionally consistent.
- `task_plan.json` should include top-level `decisions`, `milestones`, `environment`, and `dataset` whenever the source plan allows it.
- Milestones should use continuous ids like `M0..Mn` and mark `phase: v1` or `phase: phase-2` when the distinction matters.
- Phase-2 tasks must be marked `critical_path=false` so they do not block v1 DoD.

See `references/scaffold_contract.md` for the full validator-enforced rules.

## Optional Files

- Additional files for metrics, environment setup, Slurm, tracking, data pipelines, datasets, and inference may be added from full-plan context.
- Optional files must still stay under `.codex-research/` and appear in `required_files.json`.

## Operating Constraints

- Preserve existing files unless `--force` is used.
- Keep generated file paths stable for repeatable sessions.
- Do not reduce generation to keyword-only rules for advanced planning fields.
- Generate scaffolding with one Codex bundle call in `bootstrap` / `all` mode.
- Do not generate `.codex-research/run_one_task.sh` or `.codex-research/run_plan.sh`.
- Do not auto-inject execution-bypass flags into generated `.codex-research/*` files.
- The generated `workflow/CODEX.md` must contain the fixed workflow sections and the evaluator-gap rule.
- The generated Chinese execution guide must contain a dedicated read-first section for `task_plan.json`, `session_progress.md`, `decision_log.md`, and `workflow/CODEX.md`.
