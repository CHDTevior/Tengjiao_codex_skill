# Mermaid Patterns for Markdown

Use these patterns as starting points and adapt labels to the current document domain.

## 1. Workflow Flowchart

```mermaid
flowchart TD
  A[Input] --> B[Process Step 1]
  B --> C{Condition?}
  C -->|Yes| D[Branch A]
  C -->|No| E[Branch B]
  D --> F[Output]
  E --> F
```

Use for migration flows, training loops, decision gates, and execution playbooks.

## 2. Dependency Flow (Left to Right)

```mermaid
flowchart LR
  A[Source Doc/Module] --> B[Semantics Mapping]
  B --> C[Spec/API Contract]
  C --> D[Execution Tasks]
```

Use for "document relationship", "module handoff", and "pipeline ownership" sections.

## 3. Sequence Interaction

```mermaid
sequenceDiagram
  participant M as Method
  participant A as Adapter
  participant B as Backbone
  M->>A: forward(x_t, t, tt, c)
  A->>B: map kwargs + invoke
  B-->>A: F_t
  A-->>M: F_t
```

Use when call order matters more than static dependencies.

## 4. State Transition

```mermaid
stateDiagram-v2
  [*] --> Init
  Init --> Prepared: prepare_inputs
  Prepared --> Forwarded: forward
  Forwarded --> Optimized: optimizer.step
  Optimized --> [*]
```

Use when document semantics are stateful and transitions must be explicit.

## 5. Phase Timeline (Gantt)

```mermaid
gantt
  title Migration Phases
  dateFormat  YYYY-MM-DD
  section Phase A
  Compatibility skeleton :a1, 2026-03-01, 5d
  section Phase B
  Loss + consistency     :b1, after a1, 6d
  section Phase C
  Sampling + config      :c1, after b1, 5d
```

Use only when the document already owns concrete date windows.

## Placement Guidance

- Insert diagram under the nearest heading that describes the same logic.
- Avoid a standalone diagram at file end without local explanation.
- For long documents, prefer multiple small diagrams over one dense graph.
