# AGENTS.md — High-Performance Engineering Protocol

> **Target Architecture:** Optimized for high-speed "Flash" models to guarantee industrial-grade reasoning, deep code tracing, zero hallucination, and rigorous verification.

---

## 1. The Core Engineering Loop

Whenever an autonomous agent or model operates in this codebase, it must adhere to the following 5-stage pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. REVERSE ENGINEER & TRACE FIRST (ast-code-tracing)        │
│    • Never blind-grep. Trace AST symbols and call chains.   │
│    • Query Git blame/log to understand original intent.     │
│    • Calculate Blast Radius (direct and indirect callers).  │
├─────────────────────────────────────────────────────────────┤
│ 2. COGNITIVE SCAFFOLDING (sequential-thinking)              │
│    • Deconstruct requirements into testable hypotheses.     │
│    • Explicitly debate trade-offs before writing code.      │
│    • If ambiguous, HALT and clarify (sharp-edges).          │
├─────────────────────────────────────────────────────────────┤
│ 3. SENIOR MINIMALISM (ponytail)                             │
│    • YAGNI ladder: Stdlib first, native platform features.  │
│    • No unrequested abstractions, adapters, or shims.       │
│    • Leave behind exactly one runnable check.               │
├─────────────────────────────────────────────────────────────┤
│ 4. DELEGATE & REVIEW LOOP (deligate-loop)                   │
│    • Segregation of Duties: Planner -> Coder -> Reviewer.   │
│    • Strict GREEN LIGHT requirement before code is accepted.│
├─────────────────────────────────────────────────────────────┤
│ 5. ADVERSARIAL QA & SECURITY (differential-review)          │
│    • 5-axis review: Correctness, Architecture, Security.    │
│    • Root cause analysis (5-Whys), not symptom patching.    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Active S-Tier Tooling

### Configured MCP Servers (`mcp_config.json`):
* **`codebase-memory`**: Tree-sitter + Hybrid LSP for sub-millisecond AST and caller/callee tracing.
* **`sequential-thinking`**: Anthropic dynamic thought sequence loop.
* **`context7`**: Live, version-pinned documentation for all libraries.
* **`git`**: Diff, commit blame, and forensic history analysis.
* **`StitchMCP`**: Google Labs UI/UX design generation.

### Installed S-Tier Skills (`.agents/skills/`):
* **AST & Tracing**: `ast-code-tracing`, `coverage-analysis`, `codeql`, `semgrep`.
* **Cognitive Scaffolding & Philosophy**: `ponytail`, `reasoning-style`, `deligate-loop`, `doubt-driven-development`.
* **Production Quality & Anti-Rationalization**: `code-review-and-quality`, `debugging-and-error-recovery`, `test-driven-development`, `code-simplification`.
* **Security & Invariants (Trail of Bits)**: `differential-review`, `sharp-edges`, `property-based-testing`, `second-opinion`.
* **YC Sprint Discipline (Garry Tan)**: `gstack-office-hours`, `gstack-qa`, `gstack-plan-eng-review`, `gstack-careful`.

---

## 3. Anti-Rationalization Rules (Strictly Enforced)

1. **No "Trivial Fix" Exceptions:** Never skip running tests or verifying execution because a change appears small.
2. **No Mock File Inventions:** If a dependency or file is missing, halt and trace repository structure; never fabricate dummy replacements without explicit user confirmation.
3. **5-Whys Law:** When fixing a defect, trace upstream to where the invariant was first violated. Symptom patches are considered technical debt.
