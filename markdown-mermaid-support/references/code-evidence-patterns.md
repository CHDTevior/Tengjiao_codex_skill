# Code Evidence Patterns

## 1. Inline Evidence Link

Use this for short claims:

```markdown
证据：[`src/networks/openuni/transformer_sana.py:76`](../../src/networks/openuni/transformer_sana.py#L76)
```

## 2. Table Cell Link

Use this in parameter tables:

```markdown
| OpenUni Transformer | `time_embed_2` | [`openuni/transformer_sana.py:76`](../../src/networks/openuni/transformer_sana.py#L76) | 第二时间嵌入分支 |
```

## 3. Snippet Section (Auto)

Keep auto-generated snippets between markers:

```markdown
<!-- CODE-REF-SNIPPETS:START -->
## Code Reference Snippets

- [`openuni/transformer_sana.py:76`](../../src/networks/openuni/transformer_sana.py#L76)
```python
self.time_embed_2 = AdaLayerNormSingle(inner_dim)
```

<!-- CODE-REF-SNIPPETS:END -->
```

## 4. Diagram Correctness Checklist

- Each arrow reflects actual execution order.
- Optional branches are condition-labeled.
- Training and inference paths are separated or explicitly marked.
- Diagram entities appear in surrounding prose.

## 5. Common Mistakes

- Mixing unrelated loops in one linear flow.
- Using non-clickable `path:line` text only.
- Showing claims without nearby source evidence.
- Re-running tooling and creating nested links.
