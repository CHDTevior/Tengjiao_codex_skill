# Scaffold Contract

This reference defines the minimum contract that generated `.codex-research/` scaffolds must satisfy.

## task_plan.json

Top-level object:
- required: `project`, `rules`, `tasks`
- recommended: `decisions`, `milestones`, `environment`, `dataset`

Each task must contain:
- `id`
- `title`
- `description`
- `milestone`
- `feature_refs`
- `depends_on`
- `blocking_decisions`
- `steps`
- `artifacts_out`
- `acceptance`
- `passes`
- optional: `critical_path`

Validation rules:
- `depends_on` must reference existing task ids.
- every task must have at least one `acceptance` item.
- initial scaffold state requires every task `passes=false`.
- if `critical_path=false`, the task must be phase-2 / non-blocking for v1 DoD.
- milestone ids must be valid `M<number>` values and continuous like `M0..Mn`.

## feature_list.json

Each feature must contain:
- `id`
- `category`
- `task_refs`
- `description`
- `steps`
- `passes`

Validation rules:
- every feature `passes=false` in the initial scaffold.
- every `task_refs` entry must exist in `task_plan.json`.
- every task/feature mapping must be reciprocal.

## workflow/CODEX.md

Required sections:
- `Single Source of Truth`
- `Core Loop`
- `Dependency Discipline`
- `Fixed v1 Design Contracts`
- `Dataset Contract`
- `Slurm / GPU Policy`
- `Evaluation Policy`
- `Task Completion Evidence Contract`
- `GitHub Maintenance Channels`
- `Completion Gate`

Required phrases:
- `task_plan.json is the execution source of truth, feature_list.json is the capability map`
- `只能选择依赖已满足的 passes=false 任务`
- `没有证据不能改 passes=true`
- `任何 bypass 都必须写入 decision log`
- `If an evaluator is missing, record the gap and do not invent metrics.`

## execution_guide.zh-CN.md

Must include a dedicated read-first section with this order:
1. `.codex-research/task_plan.json`
2. `.codex-research/session_progress.md`
3. `.codex-research/decision_log.md`
4. `.codex-research/workflow/CODEX.md`

## Forbidden outputs

The scaffold must not generate:
- `.codex-research/run_one_task.sh`
- `.codex-research/run_plan.sh`
- bypass-approval flags such as `--dangerously-bypass-approvals-and-sandbox`
