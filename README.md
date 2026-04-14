# Tengjiao Codex Skills

Curated Codex skills for ML research workflows, with an emphasis on experiment design, training infrastructure, evaluation, and reproducibility.

## Core Research Skills

- `codex-dl-plan-harness`: Turn a deep-learning research plan into runnable scaffold files and harness manifests.
- `ml-ablation-design`: Design controlled ablation studies with synthetic-first validation and production-aligned metrics.
- `genai-evaluation-metrics`: Choose and implement evaluation metrics for generative models, including distributed evaluation concerns.
- `hydra-experiment-config`: Structure Hydra-based experiment configs for reproducible training and fast iteration.
- `wandb-experiment-tracking`: Standardize W&B logging, run metadata, grouping, and offline/online operation.
- `gpu-training-acceleration`: Improve PyTorch training throughput and memory efficiency on CUDA workloads.
- `webdataset-streaming`: Stream large tar-sharded datasets and latent caches with WebDataset.
- `hf-dataset-management`: Manage Hugging Face datasets for training, caching, upload, and verification.

## Repository Layout

Each skill lives in its own directory and usually contains:

- `SKILL.md`: The main workflow and operating instructions.
- `agents/`: Optional agent-specific guidance.
- `references/`: Supporting reference material for the skill.
- `scripts/`: Helper scripts used by the workflow when needed.

## Notes

- This repository currently also retains a few adjacent utility skills that were already present before the research curation pass.
- The backup variant `codex-dl-plan-harness.backup-*` is intentionally excluded.
