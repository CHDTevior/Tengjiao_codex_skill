---
name: codex-dl-plan-harness
description: Read an uploaded deep-learning research plan file and prepare all files needed to run the Codex DL long-running harness. Use when the user asks to convert a plan into runnable scaffold files, generate required file manifests, or regenerate the in-project mechanism document.
---

# Codex DL Plan Harness

## Workflow

1. Require user-provided plan path and target output directory.
2. Run Codex plan alignment (`scripts/normalize_plan_with_codex.sh`) to rewrite plan into deterministic structure.
3. Run `scripts/prepare_from_plan.sh` so `codex_research_harness.py` does one Codex analysis pass, then generates scaffold files with one Codex call per file (instead of one giant file bundle call).
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
- Skill runtime `codex exec` invocations (plan alignment + file generation) must run in non-interactive full-access mode (`--dangerously-bypass-approvals-and-sandbox`).
- Do not force or rewrite generated `.codex-research/*` script logic solely to inject execution flags.
- Use absolute paths when reporting generated artifacts.

## Commands

### Generate everything (default)

```bash
scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

This defaults to Codex alignment first, then framework generation.

After generation, run step-by-step task execution:

```bash
bash <project_root>/.codex-research/run_one_task.sh --target <project_root>
```

Or run multiple iterations:

```bash
bash <project_root>/.codex-research/run_plan.sh 5 --target <project_root>
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
- Confirm `.codex-research/plan/normalized_plan.md` exists when Codex alignment is enabled.
- Confirm shell scripts are executable (`init.sh`, `checks/smoke_test.sh`, `run_one_task.sh`, `run_plan.sh`).

## Notes

- Keep one-session-one-task discipline using `task_plan.json`.
- Do not set `passes=true` without test evidence.
- Regenerate files from the latest plan when scope changes.

## References

- `references/file_manifest_policy.md`
