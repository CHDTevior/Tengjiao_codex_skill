---
name: codex-dl-plan-harness
description: Read an uploaded deep-learning research plan file and prepare all files needed to run the Codex DL long-running harness. Use when the user asks to convert a plan into runnable scaffold files, generate required file manifests, or regenerate the in-project mechanism document.
---

# Codex DL Plan Harness

## Workflow

1. Require user-provided plan path and target output directory.
2. Run Codex plan alignment (`scripts/normalize_plan_with_codex.sh`) to rewrite the plan into a deterministic structure with explicit contracts.
3. Run `scripts/prepare_from_plan.sh` so `codex_research_harness.py` performs one Codex bundle call in `bootstrap` / `all` mode and returns metadata plus ordered files.
4. Let local validators reject contract drift before or during materialization.
5. Report generated artifacts, validation status, and any remaining user-owned gaps.

## Auto Execution Contract

- When this skill is triggered for plan conversion, execute the script directly; do not ask the user to copy/paste shell commands unless they explicitly ask for a command.
- Keep this skill self-contained: use only files under this skill directory (`scripts/`, `references/`, `agents/`).
- Prefer `--mode all` unless the user asks for `extract` or `gen-doc` only.
- If `--plan` is missing, stop and ask for the uploaded plan path.
- If `--target` is missing, stop and ask for the target output directory.
- Default to `--codex-plan-stage required` so plan alignment must pass before harness generation.
- Framework generation must stay Codex-driven; do not fall back to keyword-only extraction for required scaffolding decisions.
- Skill runtime `codex exec` invocations must not auto-inject execution bypass flags into generated `.codex-research/*` files.
- Do not generate `.codex-research/run_one_task.sh` or `.codex-research/run_plan.sh`.
- Use absolute paths when reporting generated artifacts.
- Environment execution examples must use non-login conda shells when wrapping commands (prefer `conda run -n <env> bash -c ...`, avoid `bash -lc`).
- Generated harness should stay resilient in fresh git repos (no `HEAD` yet): avoid hard failure when `git rev-parse HEAD` is unavailable.
- Do not fail artifact validation solely because CUDA is visible on host; fail only on actual contract violations of generated run outputs.

## Mandatory Generation Constraints

### `task_plan.json`

Every task must include:
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
- `critical_path` when the task is explicitly v1-blocking or explicitly phase-2 / non-blocking

Top-level `task_plan.json` should include, when the source allows it:
- `decisions`
- `milestones`
- `environment`
- `dataset`

### `feature_list.json`

Every feature must include:
- `id`
- `category`
- `task_refs`
- `description`
- `steps`
- `passes`

### Cross-file consistency

- Every `feature_refs` entry must resolve in `feature_list.json`.
- Every `task_refs` entry must resolve in `task_plan.json`.
- Task/feature references must be reciprocal.
- `depends_on` must only reference existing task ids.
- Milestone ids must be legal and continuous (`M0..Mn`).
- Every generated `passes` value must start as `false`.
- Every task must contain at least one `acceptance` item.
- If `critical_path=false`, the task must not block v1 DoD.
- The scaffold must support `v1` mainline versus `phase-2` enhancements instead of assuming everything is on the critical path.

## Prompt Contract

The internal Codex prompt must tell Codex to:
- do more than standardize the plan; fill missing execution contracts
- actively convert ambiguity into fixed decisions
- leave non-blocking enhancement tasks outside the v1 critical path
- fix the motion conditioning / train-eval-inference contract
- fix the metric and artifact contract
- fix the Slurm contract
- fix the dataset contract
- output files that are disk-ready, validator-ready, and executable rather than conceptual outlines
- record evaluator gaps explicitly instead of inventing metrics

## Workflow / Mechanism Contract

Generated `.codex-research/workflow/CODEX.md` must include these sections:
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

Generated `.codex-research/workflow/CODEX.md` must explicitly state:
- `task_plan.json is the execution source of truth, feature_list.json is the capability map`
- `只能选择依赖已满足的 passes=false 任务`
- `没有证据不能改 passes=true`
- `任何 bypass 都必须写入 decision log`
- `If an evaluator is missing, record the gap and do not invent metrics.`

Generated `.codex-research/execution_guide.zh-CN.md` must contain a dedicated “先看哪些文件” section with:
1. `.codex-research/task_plan.json`
2. `.codex-research/session_progress.md`
3. `.codex-research/decision_log.md`
4. `.codex-research/workflow/CODEX.md`

## Commands

### Generate everything (default)

```bash
scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

### Only extract required file manifest

```bash
scripts/prepare_from_plan.sh \
  --mode extract \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

### Overwrite existing scaffold files

```bash
scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root> \
  --force
```

### Skip Codex plan alignment (not recommended)

```bash
scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --codex-plan-stage off \
  --target <project_root>
```

### Run local scaffold validation

```bash
python3 scripts/validate_generated_harness.py \
  --target <project_root>
```

Use `--allow-progress` only when validating a scaffold that has already advanced beyond the initial all-false state.

### Optional auto-exec helper for generated projects

The skill repo also ships `scripts/run_codex_exec_loop.sh` for repositories that already contain generated `.codex-research/` files and want repeated one-task-per-run Codex execution.

Typical usage after copying the script into the target project's `scripts/` directory:

```bash
CODEX_PERMISSION_FLAGS="--dangerously-bypass-approvals-and-sandbox" \
./scripts/run_codex_exec_loop.sh 1
```

Or run it in place from the skill repo by pointing `REPO_ROOT` at the generated project:

```bash
REPO_ROOT=/path/to/generated/project \
CODEX_PERMISSION_FLAGS="--dangerously-bypass-approvals-and-sandbox" \
scripts/run_codex_exec_loop.sh 1
```

This helper is for post-generation execution only. It must not change the generation-stage rule that generated `.codex-research/*` files never auto-inject bypass flags.

## Validation Checklist

- Confirm `.codex-research/required_files.json` exists and references files that actually exist.
- Confirm `feature_list.json` and `task_plan.json` satisfy the scaffold contract in `references/scaffold_contract.md`.
- Confirm `workflow/CODEX.md` contains the required sections and evaluator-gap rule.
- Confirm `execution_guide.zh-CN.md` contains the read-first file section.
- Confirm `.codex-research/plan/normalized_plan.md` exists when Codex alignment is enabled.
- Confirm shell scripts are executable where required.

## References

- `references/file_manifest_policy.md`
- `references/scaffold_contract.md`
