# codex-dl-plan-harness

面向 Codex 的深度学习研发计划脚手架生成器。

它的定位是：把一份研究计划（plan）转换成完整的 `.codex-research/` 运行机制文件，并且支持后续按任务逐步执行。

关键变化：
- 现在不再用关键词/任务行的规则提取来决定文件内容。
- 现在由 Codex 在一次调用中返回完整文件包（含元数据+按顺序文件内容），然后本地脚本做结构校验与落盘。
- 生成流程不再自动注入 `--dangerously-bypass-approvals-and-sandbox`。

## 1. 需要什么输入

最少输入：

1. `--plan`：你的计划文件路径（Markdown 或文本）
2. `--target`：目标项目根目录

常用可选参数：

- `--codex-plan-stage required|auto|off`
  - `required`：必须先完成计划标准化（默认）
  - `auto`：尝试标准化，失败回退原计划
  - `off`：跳过标准化
- `--codex-model`：指定 Codex 模型（会传给对齐和生成两个阶段）
- `--mode all|extract|bootstrap|gen-doc`
- `--force`：覆盖已有文件

## 2. 会经过什么处理

入口：`scripts/prepare_from_plan.sh`

处理链路：

1. 参数和路径校验  
检查 `--plan`、`--target`、脚本可用性。

2. 计划标准化（可选）  
调用 `scripts/normalize_plan_with_codex.sh`，让 Codex 把原始计划整理成结构化 `normalized_plan.md`，并做 section/格式校验。

3. Codex 生成文件包（核心）  
调用 `scripts/codex_research_harness.py`。在 `bootstrap/all` 模式下，该脚本使用一次 `codex exec` + JSON schema，让 Codex 直接返回：
- `required_files`
- `feature_list`
- `task_plan`
- `files`（按 `required_files` 顺序的完整文件包）

本地脚本会进行校验：
- 必需核心文件必须齐全
- 所有路径必须位于 `.codex-research/`
- `feature_list/task_plan` 结构合法且默认 `passes=false`
- `files` 与 `required_files` 路径集合与顺序必须一致
- 不改写生成脚本去强行注入执行 bypass 参数

4. 写入目标目录  
将生成内容落盘到 `<target>/.codex-research/`，并设置 shell 文件可执行位。

5. 运行命令预检（all/bootstrap）  
在生成结束后自动预检：
- `run_one_task.sh` / `run_plan.sh` 文件存在
- `bash -n` 脚本语法检查
- 文档给出的两条运行命令做 shell 命令行语法检查

6. 给出执行下一步  
单轮：`run_one_task.sh`。  
多轮：`run_plan.sh`。

## 3. 输出是什么

默认 `--mode all` 会输出：

核心文件：
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

执行与流程文件：
- `.codex-research/init.sh`
- `.codex-research/checks/smoke_test.sh`
- `.codex-research/prompts/initializer.md`
- `.codex-research/prompts/worker.md`
- `.codex-research/workflow/CODEX.md`
- `.codex-research/run_one_task.sh`
- `.codex-research/run_plan.sh`

以及 Codex 判断需要的附加文件（例如 Slurm、metric、tracking、dataset、inference 相关配置），统一放在 `.codex-research/` 下并写入 `required_files.json`。

## 4. 常用命令

### 4.1 生成完整脚手架

```bash
bash scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

### 4.2 指定模型生成

```bash
bash scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root> \
  --codex-model <model_name>
```

### 4.3 单次执行一个任务

```bash
bash <project_root>/.codex-research/run_one_task.sh --target <project_root>
```

### 4.4 连续执行多轮

```bash
bash <project_root>/.codex-research/run_plan.sh 5 --target <project_root>
```

## 5. 设计约束

- 一次会话只做一个任务。
- 没有测试/命令证据，不要改 `passes=true`。
- 如果阻塞，保持 `passes=false` 并记录阻塞原因。
- 高复杂度字段（metric、环境、slurm、验证流程）由 Codex 基于全计划上下文生成，不退回关键词规则。

## 6. 依赖

- `bash`
- `python3`
- `codex` CLI
