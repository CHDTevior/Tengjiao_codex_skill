---
name: codex-dl-plan-harness
description: Read an uploaded deep-learning research plan file and prepare all files needed to run the Codex DL long-running harness. Use when the user asks to convert a plan into runnable scaffold files, generate required file manifests, or regenerate the in-project mechanism document.
---

# Codex DL Plan Harness

## Workflow

1. Require user-provided plan path and target output directory.
2. Run Codex plan alignment (`scripts/normalize_plan_with_codex.sh`) to rewrite plan into deterministic structure.
3. Run `scripts/prepare_from_plan.sh` so `codex_research_harness.py` uses one Codex bundle call (bootstrap/all mode) that returns required metadata plus all scaffold files in order.
4. Verify generated files under `.codex-research/`.
5. Report what was generated, and list any missing user-provided values.

## Auto Execution Contract

- When this skill is triggered for plan conversion, execute the script directly; do not ask the user to copy/paste shell commands unless they explicitly ask for a command.
- Keep this skill self-contained: use only files under this skill directory (`scripts/`, `references/`, `agents/`) and do not depend on external framework paths.
- Prefer `--mode all` unless the user asks for `extract` or `gen-doc` only.
- If `--plan` is missing, stop and ask for the uploaded plan path.
- If `--target` is missing, stop and ask for the target output directory.
- Default to `--codex-plan-stage required` so plan alignment must pass before harness generation.
- Framework generation must be Codex-driven (no fallback to keyword-only extraction for required scaffolding decisions).
- Skill runtime `codex exec` invocations (plan alignment + file generation) should not auto-inject execution bypass flags into generated `.codex-research/*` files.
- Skill output must include a Chinese execution guide: `.codex-research/execution_guide.zh-CN.md`.
- Do not generate `.codex-research/run_one_task.sh` or `.codex-research/run_plan.sh`; execution guidance should stay in `.codex-research/execution_guide.zh-CN.md`.
- The Chinese execution guide should instruct Codex to read representative task/progress docs first (for example `.codex-research/task_plan.json`, `.codex-research/session_progress.md`, `.codex-research/decision_log.md`) and use `.codex-research/workflow/CODEX.md` for process-level guidance.
- When `.codex-research/workflow/CODEX.md` is generated, it must include a dedicated GitHub maintenance channel section (Issues/PRs/Discussions/Projects) for project management.
- Use absolute paths when reporting generated artifacts.
- Environment execution examples must use non-login conda shells when wrapping commands (prefer `conda run -n <env> bash -c ...`, avoid `bash -lc` to prevent env reset).
- Generated harness should be resilient in fresh git repos (no `HEAD` yet): avoid hard failure when `git rev-parse HEAD` is unavailable.
- Do not fail artifact validation solely because CUDA is visible on host; fail only on actual contract violations of generated run outputs.
- T001 scaffold generation must include both `scripts/setup_env.sh` and `.codex-research/checks/validate_env.sh` when task plan requires them.

## Commands

### Generate everything (default)

```bash
scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

This defaults to Codex alignment first, then framework generation.

After generation, read the Chinese execution guide:

```bash
cat <project_root>/.codex-research/execution_guide.zh-CN.md
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

## Validation Checklist

- Confirm `.codex-research/required_files.json` exists.
- Confirm `.codex-research/feature_list.json` is valid JSON list.
- Confirm `.codex-research/task_plan.json` has a valid top-level `tasks` list.
- Confirm `.codex-research/MECHANISM.md` exists and references the source plan path.
- Confirm `.codex-research/execution_guide.zh-CN.md` exists.
- Confirm `.codex-research/plan/normalized_plan.md` exists when Codex alignment is enabled.
- Confirm shell scripts are executable (`init.sh`, `checks/smoke_test.sh`).
- Confirm required scaffold directories exist at generation time: `src/`, `scripts/`, `artifacts/`, `artifacts/data/`, `artifacts/logs/`, `artifacts/models/`.
- Confirm `.codex-research/checks/validate_env.sh` exists and passes basic checks in target env.
- Confirm `scripts/setup_env.sh` exists and is executable; if delegating to `.codex-research/scripts/set_env.sh`, ensure both paths are present.
- Confirm `.codex-research/execution_guide.zh-CN.md` explicitly tells Codex to read task/progress docs and `.codex-research/workflow/CODEX.md`.
- Confirm `.codex-research/workflow/CODEX.md` includes the GitHub maintenance channel section.

## Notes

- Keep one-session-one-task discipline using `task_plan.json`.
- Do not set `passes=true` without test evidence.
- Regenerate files from the latest plan when scope changes.
- Incident hardening (2026-03-04): prioritize preventing preflight/config mismatches that block first run before any task code executes.

## References

- `references/file_manifest_policy.md`
