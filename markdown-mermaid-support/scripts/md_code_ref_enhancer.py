#!/usr/bin/env python3
"""
Enhance Markdown code references.

Features:
1) Convert `path/to/file.py:123` into a clickable Markdown link.
2) Append/update an auto-generated snippet section with referenced source lines.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


REF_RE = re.compile(r"(?<!\[)`(?P<path>[A-Za-z0-9_./-]+\.[A-Za-z0-9_+-]+):(?P<line>\d+)`")
NESTED_LINK_RE = re.compile(
    r"\[\[`(?P<label>[A-Za-z0-9_./-]+\.[A-Za-z0-9_+-]+:\d+)`\]\((?P<link>[^)]+)\)\]\((?P=link)\)"
)
SNIPPET_START = "<!-- CODE-REF-SNIPPETS:START -->"
SNIPPET_END = "<!-- CODE-REF-SNIPPETS:END -->"


def guess_lang(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".md": "markdown",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".sh": "bash",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
    }.get(ext, "")


def build_file_index(repo_root: Path) -> List[str]:
    files: List[str] = []
    for p in repo_root.rglob("*"):
        if p.is_file() and ".git" not in p.parts:
            files.append(p.relative_to(repo_root).as_posix())
    return files


def resolve_ref(raw_path: str, repo_root: Path, file_index: Sequence[str]) -> Optional[str]:
    direct = (repo_root / raw_path)
    if direct.is_file():
        return raw_path

    suffix_matches = [p for p in file_index if p.endswith(raw_path)]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    if len(suffix_matches) > 1:
        src_matches = [p for p in suffix_matches if p.startswith("src/")]
        if len(src_matches) == 1:
            return src_matches[0]
        if len(src_matches) > 1:
            net_matches = [p for p in src_matches if "/networks/" in p]
            if len(net_matches) == 1:
                return net_matches[0]

    if not raw_path.startswith("src/"):
        src_try = f"src/{raw_path}"
        src_matches = [p for p in file_index if p == src_try or p.endswith(src_try)]
        if len(src_matches) == 1:
            return src_matches[0]

    return None


def extract_code_line(repo_root: Path, rel_path: str, line_no: int) -> str:
    target = repo_root / rel_path
    if not target.is_file():
        return "<missing file>"
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    if line_no < 1 or line_no > len(lines):
        return "<line out of range>"
    return lines[line_no - 1].rstrip()


def link_for(md_path: Path, repo_root: Path, target_rel: str, line_no: int) -> str:
    target_abs = (repo_root / target_rel).resolve()
    rel_link = os.path.relpath(str(target_abs), str(md_path.parent.resolve())).replace(os.sep, "/")
    return f"{rel_link}#L{line_no}"


def transform_markdown(
    md_path: Path,
    repo_root: Path,
    file_index: Sequence[str],
    append_snippets: bool,
) -> Tuple[str, List[str]]:
    text = md_path.read_text(encoding="utf-8")
    text = NESTED_LINK_RE.sub(r"[`\g<label>`](\g<link>)", text)
    lines = text.splitlines()
    in_fence = False
    unresolved: List[str] = []
    references: Dict[Tuple[str, int], Tuple[str, str]] = {}
    out_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out_lines.append(line)
            continue

        if in_fence:
            out_lines.append(line)
            continue

        def repl(match: re.Match[str]) -> str:
            raw_path = match.group("path")
            line_no = int(match.group("line"))
            resolved = resolve_ref(raw_path, repo_root, file_index)
            raw_ref = f"{raw_path}:{line_no}"
            if not resolved:
                unresolved.append(raw_ref)
                return match.group(0)

            link = link_for(md_path, repo_root, resolved, line_no)
            code_line = extract_code_line(repo_root, resolved, line_no)
            references[(resolved, line_no)] = (raw_ref, code_line)
            return f"[`{raw_ref}`]({link})"

        out_lines.append(REF_RE.sub(repl, line))

    out_text = "\n".join(out_lines) + ("\n" if text.endswith("\n") else "")

    if append_snippets and references:
        snippet_lines: List[str] = []
        snippet_lines.append(SNIPPET_START)
        snippet_lines.append("## Code Reference Snippets")
        snippet_lines.append("")
        for (resolved, line_no), (raw_ref, code_line) in sorted(references.items()):
            lang = guess_lang(resolved)
            link = link_for(md_path, repo_root, resolved, line_no)
            snippet_lines.append(f"- [`{raw_ref}`]({link})")
            snippet_lines.append(f"```{lang}")
            snippet_lines.append(code_line if code_line else "<empty line>")
            snippet_lines.append("```")
            snippet_lines.append("")
        snippet_lines.append(SNIPPET_END)
        snippet_block = "\n".join(snippet_lines).rstrip() + "\n"

        if SNIPPET_START in out_text and SNIPPET_END in out_text:
            pre = out_text.split(SNIPPET_START, 1)[0].rstrip()
            post = out_text.split(SNIPPET_END, 1)[1].lstrip("\n")
            out_text = f"{pre}\n\n{snippet_block}\n{post}"
        else:
            out_text = out_text.rstrip() + "\n\n" + snippet_block

    return out_text, sorted(set(unresolved))


def main() -> None:
    parser = argparse.ArgumentParser(description="Enhance Markdown code references.")
    parser.add_argument("--repo-root", required=True, help="Repository root for path resolution.")
    parser.add_argument("--files", nargs="+", required=True, help="Markdown files to process.")
    parser.add_argument("--write", action="store_true", help="Write back to files.")
    parser.add_argument(
        "--append-snippets",
        action="store_true",
        help="Append/update CODE-REF snippets section.",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    file_index = build_file_index(repo_root)

    all_unresolved: Dict[str, List[str]] = {}
    for fp in args.files:
        md_path = Path(fp).resolve()
        transformed, unresolved = transform_markdown(
            md_path=md_path,
            repo_root=repo_root,
            file_index=file_index,
            append_snippets=args.append_snippets,
        )
        if args.write:
            md_path.write_text(transformed, encoding="utf-8")
        else:
            print(transformed)
        if unresolved:
            all_unresolved[str(md_path)] = unresolved

    if all_unresolved:
        print("Unresolved references:", flush=True)
        for file_path, refs in all_unresolved.items():
            print(f"- {file_path}")
            for ref in refs:
                print(f"  - {ref}")


if __name__ == "__main__":
    main()
