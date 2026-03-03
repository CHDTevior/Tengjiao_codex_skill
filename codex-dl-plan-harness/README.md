# codex-dl-plan-harness

一个面向 Codex 的深度学习研发计划脚手架生成器。

目标：把一份“研究/开发计划文档”转换成可执行的长期开发机制，包括任务清单、会话规则、检查脚本、以及自动化执行脚本（一次一个任务或循环执行）。

## 1. 核心逻辑

- 先把原始计划整理成结构化计划（可选但推荐，使用 Codex 对齐）。
- 从计划中提取关键信号（如 slurm、wandb、evaluation 等）与任务条目。
- 生成 `.codex-research/` 目录下的标准文件（spec、task_plan、checks、prompts、workflow、run scripts 等）。
- 通过 `run_one_task.sh` 强制“一次只做一个任务”的执行节奏。
- 通过 `run_plan.sh` 批量循环多轮执行，直到任务完成或达到轮数上限。

## 2. 需要的输入

最少需要两个输入：

1. `--plan`：你的计划文件路径（Markdown 或文本）
2. `--target`：目标项目根目录（脚手架输出位置）

可选输入：

- `--codex-plan-stage`：`required|auto|off`
  - `required`：必须先完成 Codex 对齐（默认）
  - `auto`：尝试对齐，失败则回退原计划
  - `off`：不做对齐，直接使用原计划
- `--codex-model`：指定 Codex 模型
- `--force`：覆盖已存在文件
- `--mode`：`all|extract|bootstrap|gen-doc`

## 3. 一步步处理流程

入口脚本：`scripts/prepare_from_plan.sh`

处理链路如下：

1. 参数校验
- 检查 `--plan`、`--target` 是否存在
- 检查基础脚本是否可用

2. 计划对齐（可选）
- 调用 `scripts/normalize_plan_with_codex.sh`
- 让 Codex 输出标准化结构的 `normalized_plan.md`
- 验证 section 完整性与格式约束

3. 生成清单与脚手架
- 调用 `scripts/codex_research_harness.py`
- 提取 tasks、headings、signals
- 生成 `required_files` / `feature_list` / `task_plan`
- 根据模板写入 `.codex-research/*`

4. 生成机制说明
- 生成 `.codex-research/MECHANISM.md`

5. 给出下一步执行命令
- 运行单任务：`.codex-research/run_one_task.sh`
- 运行多轮：`.codex-research/run_plan.sh`

## 4. 输出是什么

默认 `--mode all` 会在 `<target>/.codex-research/` 生成：

核心文件：

- `research_spec.md`
- `required_files.json`
- `required_files.generated.json`
- `feature_list.json`
- `task_plan.json`
- `session_progress.md`
- `decision_log.md`
- `run_registry.jsonl`
- `MECHANISM.md`

执行与流程文件：

- `init.sh`
- `checks/smoke_test.sh`
- `workflow/CODEX.md`
- `run_one_task.sh`
- `run_plan.sh`
- `prompts/initializer.md`
- `prompts/worker.md`

可选文件（按计划信号触发）：

- `slurm/train.sbatch`, `slurm/debug.sbatch`
- `config/wandb.yaml`
- `config/hf_dataset.yaml`
- `config/webdataset.yaml`
- `config/eval.yaml`
- `config/inference.yaml`

## 5. 常用命令

### 5.1 生成完整脚手架

```bash
bash scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

### 5.2 生成后，按任务执行（一次一个）

```bash
bash <project_root>/.codex-research/run_one_task.sh --target <project_root>
```

### 5.3 连续执行 N 轮

```bash
bash <project_root>/.codex-research/run_plan.sh 5 --target <project_root>
```

## 6. 执行约束（建议遵守）

- 每个会话只处理一个 `passes=false` 任务。
- 无测试/命令证据，不要将任务标记为 `passes=true`。
- 如果阻塞（凭据/外部依赖等），保持 `passes=false`，写明阻塞原因并停止。

## 7. 依赖

- `bash`
- `python3`
- `codex` CLI（用于计划对齐与任务执行）
