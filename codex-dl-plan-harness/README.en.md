# codex-dl-plan-harness

A Codex-oriented scaffold generator for deep-learning research plans.

Its purpose is to turn a research plan into a complete `.codex-research/` operating scaffold so Codex can execute the work task by task afterward.

## 1. Key Changes

- File contents are no longer decided by keyword extraction or task-line heuristics.
- Codex now returns the full file bundle in a single call, including metadata and ordered file contents, and local scripts only validate and materialize the results.
- The generation flow no longer auto-injects `--dangerously-bypass-approvals-and-sandbox`.
- If `.codex-research/workflow/CODEX.md` is generated, the script ensures it includes a `GitHub Maintenance Channels` section covering Issues, Pull Requests, Discussions, and Projects.

## 2. Required Inputs

Minimum required inputs:

1. `--plan`: path to the plan file (Markdown or plain text)
2. `--target`: target project root directory

Common optional arguments:

- `--codex-plan-stage required|auto|off`
  - `required`: plan normalization must succeed first (default)
  - `auto`: try normalization, fall back to the original plan if it fails
  - `off`: skip normalization
- `--codex-model`: choose the Codex model used for both alignment and generation
- `--mode all|extract|bootstrap|gen-doc`
- `--force`: overwrite existing files

## 3. Processing Flow

Entry point: `scripts/prepare_from_plan.sh`

Pipeline:

1. Parameter and path validation  
   Checks `--plan`, `--target`, and required script availability.

2. Plan normalization (optional)  
   Calls `scripts/normalize_plan_with_codex.sh` so Codex rewrites the raw plan into a structured `normalized_plan.md` with section and formatting validation.

3. Codex file-bundle generation (core step)  
   Calls `scripts/codex_research_harness.py`. In `bootstrap` or `all` mode, it uses a single `codex exec` call plus a JSON schema so Codex directly returns:
   - `required_files`
   - `feature_list`
   - `task_plan`
   - `files` (the complete ordered file bundle matching `required_files`)

   Local validation then checks:
   - all required core files are present
   - every path stays inside `.codex-research/`
   - `feature_list` and `task_plan` have valid structure and default to `passes=false`
   - `files` matches `required_files` in both path set and order
   - generated scripts are not rewritten to force bypass flags
   - if `.codex-research/workflow/CODEX.md` exists, the GitHub maintenance section is inserted exactly once when missing

4. Write into the target directory  
   Writes generated outputs into `<target>/.codex-research/` and marks shell scripts as executable.

5. Provide next-step execution guidance  
   The workflow does not generate `run_one_task.sh` or `run_plan.sh`. Instead, it emits `.codex-research/execution_guide.zh-CN.md`, which tells Codex to:
   - read the current progress documents first: `task_plan.json`, `session_progress.md`, `decision_log.md`
   - use `.codex-research/workflow/CODEX.md` for process guidance
   - advance one task per session and write progress back into the research docs

## 4. Outputs

By default, `--mode all` produces:

Core files:

- `.codex-research/research_spec.md`
- `.codex-research/feature_list.json`
- `.codex-research/task_plan.json`
- `.codex-research/required_files.json`
- `.codex-research/required_files.generated.json`
- `.codex-research/session_progress.md`
- `.codex-research/decision_log.md`
- `.codex-research/run_registry.jsonl`
- `.codex-research/MECHANISM.md`
- `.codex-research/execution_guide.zh-CN.md`

Execution and workflow files:

- `.codex-research/init.sh`
- `.codex-research/checks/smoke_test.sh`
- `.codex-research/prompts/initializer.md`
- `.codex-research/prompts/worker.md`
- `.codex-research/workflow/CODEX.md`

Additional files that Codex determines are necessary, such as Slurm, metrics, tracking, dataset, or inference-related configs, are also written under `.codex-research/` and listed in `required_files.json`.

## 5. Common Commands

### 5.1 Generate the full scaffold

```bash
bash scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

### 5.2 Generate with a specific model

```bash
bash scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root> \
  --codex-model <model_name>
```

### 5.3 Read the execution guide

```bash
cat <project_root>/.codex-research/execution_guide.zh-CN.md
```

### 5.4 Recommended prompt for Codex

```text
Please read .codex-research/task_plan.json, .codex-research/session_progress.md,
.codex-research/decision_log.md first, and follow the process in
.codex-research/workflow/CODEX.md. Pick one task with passes=false, advance it,
write progress and decisions back, and only set passes=true when you have
verification evidence.
```

## 6. Design Constraints

- One session should work on one task only.
- Do not set `passes=true` without test or command evidence.
- If blocked, keep `passes=false` and record the blocking reason.
- High-complexity fields such as metrics, environment, Slurm, and validation flow are generated by Codex from full-plan context instead of falling back to keyword rules.

## 7. Dependencies

- `bash`
- `python3`
- `codex` CLI
