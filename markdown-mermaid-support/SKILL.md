---
name: markdown-mermaid-support
description: Create or revise technical Markdown documents that need Mermaid diagrams, flow validation, and source-code evidence links. Use when docs describe workflows/dependencies/branches and should include clickable file:line references plus concrete code snippets.
---

# Markdown Mermaid Support

Use this skill to produce high-clarity technical Markdown with two outcomes:
1. Correct Mermaid diagrams for process and dependency logic.
2. Clickable code references with concrete source snippets.

## Workflow

1. Identify sections that need diagrams.
- Prefer Mermaid when logic has 3+ steps, branching, or module handoffs.
- Use `flowchart` for process/dependency, `sequenceDiagram` for interaction timelines.

2. Validate diagram semantics before writing.
- Verify node order matches real execution order.
- Explicitly show optional branches and gate conditions.
- Do not mix training loop and inference loop in one path unless clearly separated.

3. Add/refresh code evidence links.
- Convert `path/to/file.py:123` to clickable markdown links.
- Keep references near the owning sentence/table.
- Add a code snippet section for referenced lines.

4. Run the bundled enhancer script when editing docs.

```bash
scripts/md_code_ref_enhancer.py \
  --repo-root <repo-root> \
  --files <doc1.md> [<doc2.md> ...] \
  --write \
  --append-snippets
```

5. Re-check rendering.
- Mermaid blocks must render in Markdown preview.
- Links must jump to the target file and line.
- Snippets must match referenced lines.

## Authoring Rules

- Keep diagrams local to the section they explain.
- Keep each diagram focused on one question.
- Keep labels short and action-oriented.
- Avoid oversized diagrams; split by concern.
- Prefer idempotent doc updates (re-running script should not duplicate links/snippets).

## References

- Mermaid templates: `references/mermaid-patterns.md`
- Code evidence patterns: `references/code-evidence-patterns.md`
