# codex-dl-plan-harness

[直接简单的使用图文，可以跳转到这个云文档学习如何快速上手使用](https://my.feishu.cn/wiki/KriYwDYYXi0t6akCxyNcAWAynMd?from=from_copylink)

把研究计划转换成可落盘、可校验、可执行的 `.codex-research/` 脚手架。

当前版本重点防止五类常见缺陷：
- 任务 / 功能漂移
- 缺失依赖
- 关键技术合同歧义
- 评估定义不完整
- Slurm 规则不可执行

## 核心变化

- `task_plan.json` / `feature_list.json` 的结构约束更严格，强制双向映射一致。
- prompt 不再只做“标准化计划”，而是要求补齐执行合同。
- `workflow/CODEX.md` 与 `execution_guide.zh-CN.md` 的关键流程约束改为本地稳定模板，减少模型漂移。
- 生成的 `workflow/CODEX.md` 会固定包含 GitHub maintenance channel 约束，覆盖 Issues / Pull Requests / Discussions / Projects。
- 新增本地 validator：`scripts/validate_generated_harness.py`。
- 默认生成流程会自动做本地校验；验证失败直接阻断落盘结果进入“看起来生成成功”的假状态。

## 生成流程

入口脚本：`scripts/prepare_from_plan.sh`

处理链路：
1. 校验 `--plan` / `--target`
2. 运行 `scripts/normalize_plan_with_codex.sh`
3. 运行 `scripts/codex_research_harness.py`
4. 本地校验：task / feature / milestone / CODEX.md / 执行指南合同
5. 写入目标目录

## 输出文件说明

默认 `--mode all` 会在目标目录生成 `.codex-research/`，其中常见核心文件作用如下：

- `research_spec.md`：把原始研究计划整理成项目内可读的研究规格说明。
- `feature_list.json`：能力映射表，描述有哪些 feature，以及每个 feature 对应哪些任务。
- `task_plan.json`：执行真相源，定义任务顺序、依赖、验收标准、关键路径与 phase 划分。
- `required_files.json`：最终应存在的 scaffold 文件清单，是落盘后的正式 manifest。
- `required_files.generated.json`：生成阶段导出的 manifest 快照，便于对比和调试。
- `session_progress.md`：记录最近一次或最近几次执行进展、证据、阻塞点和下一步。
- `decision_log.md`：记录固定设计决策、绕过说明和 evaluator / contract gap。
- `run_registry.jsonl`：按行记录每次关键运行的命令、seed、commit、job id、artifact 路径。
- `MECHANISM.md`：说明当前项目内 harness 机制和生成来源。
- `execution_guide.zh-CN.md`：给后续 Codex 会话的中文执行说明，强调先看哪些文件、怎么选任务、何时更新 `passes`。
- `workflow/CODEX.md`：流程级操作合同，写死 single source of truth、依赖纪律、Slurm / GPU 规则、评估规则和 completion gate。
- `init.sh`：项目初始化入口脚本，放最基础的 scaffold 初始化动作。
- `checks/smoke_test.sh`：最小 smoke test，用于快速验证 scaffold 基本可运行。
- `prompts/initializer.md`：给初始化型 Codex 会话使用的提示词模板。
- `prompts/worker.md`：给执行单任务型 Codex 会话使用的提示词模板。

此外，Codex 还可以根据计划内容生成额外文件，例如：
- 数据集合同或数据检查脚本
- Slurm / GPU 运行脚本或配置
- metric / evaluator 说明与检查文件
- 训练、推理、复现实验相关的辅助配置文件

## 强制字段

### `task_plan.json`

每个 task 必须有：
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
- 如适用：`critical_path`

顶层推荐生成：
- `decisions`
- `milestones`
- `environment`
- `dataset`

### `feature_list.json`

每个 feature 必须有：
- `id`
- `category`
- `task_refs`
- `description`
- `steps`
- `passes`

## 本地校验规则

默认 validator 会检查：
- `depends_on` 是否只引用存在的 task id
- `feature_refs` / `task_refs` 是否双向一致
- milestone id 是否合法且连续（`M0..Mn`）
- 每个任务是否至少有一个 `acceptance`
- 初始 scaffold 的 `passes` 是否全为 `false`
- `critical_path=false` 的任务是否被正确放在 phase-2 / 非阻塞位置
- `workflow/CODEX.md` 是否包含固定章节
- `workflow/CODEX.md` 是否明确写出 evaluator 缺失时只能记录 gap，不能虚构指标
- `execution_guide.zh-CN.md` 是否包含“先看哪些文件”段落

## 常用命令

### 生成完整脚手架

```bash
bash scripts/prepare_from_plan.sh \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

### 只抽取 manifest

```bash
bash scripts/prepare_from_plan.sh \
  --mode extract \
  --plan <uploaded_plan_file> \
  --target <project_root>
```

### 独立运行 validator

```bash
python3 scripts/validate_generated_harness.py \
  --target <project_root>
```

如果是已经推进过若干任务的项目，用：

```bash
python3 scripts/validate_generated_harness.py \
  --target <project_root> \
  --allow-progress
```

### 自动执行计划辅助脚本

仓库内提供：
- `scripts/run_codex_exec_loop.sh`

用途：
- 针对已经由本 skill 生成 `.codex-research/` 的项目，批量调用 `codex exec`
- 每次 run 只推进一个满足依赖的 task
- 遇到失败、环境阻塞、外部 Slurm job 未完成时立即停止
- 把每轮输出写入 `.codex-research/logs/`

如果你直接在目标项目根目录里放置这个脚本，可按下面方式运行：

```bash
CODEX_PERMISSION_FLAGS="--dangerously-bypass-approvals-and-sandbox" \
./scripts/run_codex_exec_loop.sh 1
```

如果脚本仍放在 skill 仓库里，而目标项目在别处，可这样运行：

```bash
REPO_ROOT=/path/to/generated/project \
CODEX_PERMISSION_FLAGS="--dangerously-bypass-approvals-and-sandbox" \
/path/to/Tengjiao_codex_skill/codex-dl-plan-harness/scripts/run_codex_exec_loop.sh 1
```

传额外 `codex exec` 参数：

```bash
REPO_ROOT=/path/to/generated/project \
CODEX_PERMISSION_FLAGS="--dangerously-bypass-approvals-and-sandbox" \
/path/to/Tengjiao_codex_skill/codex-dl-plan-harness/scripts/run_codex_exec_loop.sh 5 -- --model gpt-5-codex
```

说明：
- 默认 `CODEX_PERMISSION_FLAGS` 是 `--ask-for-approval never`
- 只有你显式设置时，才会使用 `--dangerously-bypass-approvals-and-sandbox`
- 这个 helper 不会改变 skill 生成阶段“不自动注入 bypass flags 到生成文件”的规则

## 如何确认增强已生效

生成完成后，至少检查这几项：
- `task_plan.json` 的每个 task 都有 `milestone`、`feature_refs`、`depends_on`、`blocking_decisions`、`artifacts_out`、`acceptance`
- `feature_list.json` 的每个 feature 都有 `task_refs`
- `task_plan.json` 与 `feature_list.json` 双向引用一致
- `workflow/CODEX.md` 含固定章节，并明确写出 evaluator 缺失时只能记录 gap，不能虚构指标
- `execution_guide.zh-CN.md` 含 “先看哪些文件” 段落

## 最小示例输入计划

```md
# Motion control plan

Goal: build a v1 text+trajectory to motion pipeline, then add a phase-2 tokenizer enhancement.

Constraints:
- v1 must be runnable on Slurm GPU nodes
- dataset is HumanML3D
- metrics must be explicit; if an evaluator is missing, record the gap
- inference must use planner trajectory
- evaluation must separate oracle vs end-to-end

Needed work:
- v1 mainline: dataset contract, planner, motion conditioning, end-to-end inference
- phase-2: Traj-VQ comparison branch
```

## 预期输出摘要

- `task_plan.json` 会包含 `decisions`、`milestones`、`environment`、`dataset`
- v1 主线任务与 phase-2 增强任务会区分开，不会默认全部位于关键路径
- phase-2 任务应设置 `critical_path=false`
- `workflow/CODEX.md` 会固定写入执行真相源、依赖纪律、Slurm / GPU 规则、评估规则、完成门槛
- `execution_guide.zh-CN.md` 会固定引导 Codex 先读：
  - `task_plan.json`
  - `session_progress.md`
  - `decision_log.md`
  - `workflow/CODEX.md`

## 参考

- `references/file_manifest_policy.md`
- `references/scaffold_contract.md`
