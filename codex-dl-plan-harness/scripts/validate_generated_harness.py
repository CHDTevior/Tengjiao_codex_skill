#!/usr/bin/env python3
"""Validate a generated .codex-research scaffold."""

from __future__ import annotations

import argparse
from pathlib import Path

from codex_research_harness import validate_scaffold_directory


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated Codex DL harness outputs.")
    parser.add_argument("--target", required=True, help="Target project root")
    parser.add_argument(
        "--allow-progress",
        action="store_true",
        help="Allow passes=true for scaffolds that have already progressed beyond the initial state.",
    )
    args = parser.parse_args()

    result = validate_scaffold_directory(
        Path(args.target).resolve(),
        expect_initial_state=not args.allow_progress,
    )
    print(
        "[validate] ok "
        f"target={result['target']} tasks={result['task_count']} "
        f"features={result['feature_count']} milestones={result['milestone_count']} "
        f"expect_initial_state={result['expect_initial_state']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
