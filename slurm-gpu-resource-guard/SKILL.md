---
name: slurm-gpu-resource-guard
description: Manage ts1v23 Slurm GPU availability on Iridis by checking active allocations, deciding whether remaining walltime is sufficient for training/debug, and submitting renewal jobs with gpu-jupyter.sh (H100), gpu-jupyter2.sh (A100), gpu-jupyter_ecs_a100.sh (swarm_a100 A100), gpu-jupyter3.sh (quad_h200 H200), or gpu-jupyter_dualh200.sh (dual_h200 H200). Use when the user asks to check current GPU resources, renew cards due to low remaining time, or run debug commands on allocated compute nodes.
---

# Slurm GPU Resource Guard

## Overview

Check current Slurm GPU jobs for `ts1v23`, decide whether resources are sufficient, and submit renewal jobs when needed. For debug/training work, always SSH to the allocated compute node first, then run commands inside that node.

Preferred launch mode for long training in this environment:
- `ssh <node>` -> init conda shell -> `conda activate <env>` -> set `LD_LIBRARY_PATH` -> `nohup python ... &` -> confirm PID/log -> extended monitor -> `exit`
- Avoid launching long training through transient `srun` steps unless explicitly requested.
- For Slurm-scheduled training/debug commands in this workflow, default to `nohup` background launch unless the user explicitly asks for foreground execution.

## Conda Environment Requirement

- The user should provide an explicit conda environment name for each task.
- If environment name is missing, stop before any training/debug launch and ask the user which environment to use.
- Do not guess or silently choose a default environment.
- Exception: the shared `gpu-jupyter*.sh` helper scripts are infrastructure scripts, not training jobs. They should always initialize conda from `/scratch/ts1v23/.conda/etc/profile.d/conda.sh` and activate `base`, because Jupyter is maintained in the base environment.

## Resource Limits And Scripts

- Hard limits:
  - H100 (`swarm_h100`): `5-00:00:00`
  - A100 (`a100`): `2-12:00:00`
  - A100 (`swarm_a100`): `5-00:00:00`
  - H200 (`quad_h200`): `2-12:00:00`
  - H200 (`dual_h200`): `2-12:00:00`
- Submission scripts (under `/scratch/ts1v23`):
  - H100: `gpu-jupyter.sh`
  - A100 (`a100`): `gpu-jupyter2.sh`
  - A100 (`swarm_a100`, 2 GPUs, 5 days): `gpu-jupyter_ecs_a100.sh`
  - H200 (`quad_h200`): `gpu-jupyter3.sh`
  - H200 (`dual_h200`): `gpu-jupyter_dualh200.sh`
- Jupyter helper script conventions:
  - Use `set -euo pipefail`.
  - Use `#SBATCH --output=logs/%j.log` and `#SBATCH --error=logs/%j.log`.
  - Use `source /scratch/ts1v23/.conda/etc/profile.d/conda.sh` then `conda activate base`.
  - Use `export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"` before `jupyter notebook ...`.

## Workflow

1. Check queue first on every training/debug request:
```bash
squeue -lu ts1v23
squeue -u ts1v23 -o '%.10i %.12P %.18j %.10T %.10M %.10l %.10L %.20R'
```
2. Decide whether time is sufficient for the requested task:
   - If user gives expected duration, compare against `TIME_LEFT` directly.
   - If user does not specify duration, use defaults:
     - training: require at least `1-00:00:00`
     - debug: require at least `02:00:00`
   - Treat as insufficient when no relevant `RUNNING`/`PENDING` job exists on the target partition, or all relevant jobs are below required `TIME_LEFT`.
3. Renew card when insufficient:
```bash
cd /scratch/ts1v23
sbatch gpu-jupyter.sh    # H100
sbatch gpu-jupyter2.sh   # A100
sbatch gpu-jupyter_ecs_a100.sh   # A100 (swarm_a100, 2 GPUs, 5 days)
sbatch gpu-jupyter3.sh   # H200 (quad_h200)
sbatch gpu-jupyter_dualh200.sh   # H200 (dual_h200)
```
4. Confirm renewal result and report job id/state:
```bash
squeue -u ts1v23 -o '%.10i %.12P %.18j %.10T %.10M %.10l %.10L %.20R'
```

## Training Guardrails (Merged)

### Offline-First Defaults

Set offline defaults before training unless user explicitly needs online access:

```bash
export HF_DATASETS_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
```

Pre-cache models/datasets on login node before compute-node launch.

### Preflight Before Launch

Before `nohup python ...`, validate critical inputs:
- dataset/cache paths exist
- required shards/files are present
- model weights/checkpoints exist
- required env vars are present (`WANDB_API_KEY`, data roots, etc.)

Fail fast on missing prerequisites; do not launch training with partial setup.

### Conda Init In Non-Interactive Context

On compute nodes, do not call `conda activate` directly. Use:

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate <env_name>
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
```

For the shared `gpu-jupyter*.sh` allocation scripts in `/scratch/ts1v23`, prefer the fixed absolute init path instead of relying on shell state:

```bash
source /scratch/ts1v23/.conda/etc/profile.d/conda.sh
conda activate base
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
```

### Log Naming

For Slurm-submitted jobs, use job-id-only logs:

```bash
#SBATCH --output=%j.log
#SBATCH --error=%j.log
```

Avoid date-stamped or mixed naming patterns.

## Debug Execution Rule

Always debug on the compute node that holds the allocation.

1. Find node from running job:
```bash
squeue -u ts1v23 -o '%.10i %.12P %.10T %.20R'
```
2. If job is `RUNNING` and node exists (e.g. `swarmh1002`, `blossom04`), SSH first:
```bash
ssh <node_name>
```
3. Run debug commands only after entering the node.
4. If job is `PENDING` (no node), do not run debug commands; report waiting reason and renew if needed.

## Long Training Launch Rule (SSH + nohup)

When the user wants persistent training on an already allocated node, use this sequence:

1. Find allocated node:
```bash
squeue -u ts1v23 -o '%.10i %.12P %.10T %.20R %.10L'
```
2. SSH into node:
```bash
ssh <node_name>
```
3. Activate the user-specified conda environment with non-interactive-safe init:
```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate <env_name>
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
```
4. Set offline defaults (unless user asks for online):
```bash
export HF_DATASETS_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
```
5. Launch training with `nohup` from project root:
```bash
nohup python -u train_vq.py ... > logs/<run>.log 2>&1 < /dev/null &
echo $!   # record PID
```
6. Verify process and log growth before leaving:
```bash
ps -p <pid> -o pid,etime,cmd
tail -n 40 logs/<run>.log
```
7. Extended monitoring window after launch:
   - Monitor for at least `10 minutes` by default before detaching.
   - For expensive/full runs, prefer `15 minutes`.
   - Confirm: no import crash, no immediate OOM, loss is non-NaN and changing, throughput is plausible.
```bash
for i in {1..20}; do date '+%H:%M:%S'; tail -n 20 logs/<run>.log; sleep 30; done
```
8. Exit session after successful monitoring:
```bash
exit
```

## Fail-Fast Rules

- Do not assume old allocations are still valid; always run queue check first.
- Do not run GPU-heavy debug on login nodes.
- Do not silently continue when `ssh` to node fails; stop and report the exact error.
- Do not start training/debug command before activating a user-specified conda environment.
- If no conda environment is provided by the user, stop and ask; do not guess.
- Do not submit duplicate renewals repeatedly; check for existing `PENDING` job on the same partition before submitting again.
- Do not detach blindly: always record `PID`, log file path, and first successful training lines.
- Do not run `pip install` / model downloads inside active compute training jobs.
- For sbatch scripts used in this workflow, require `set -euo pipefail`.
