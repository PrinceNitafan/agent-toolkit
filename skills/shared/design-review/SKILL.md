---
name: design-review
description: "Stress-test system designs, module contracts, and architectural plans before implementation by resolving dependency-tree decision frontiers with the user. Trigger with /design-review."
---

# Architectural Design Review & Frontier Resolution (`/design-review`)

Goal: surface hidden coupling, contract ambiguities, failure modes, and environment hazards before writing implementation code by resolving open architectural decisions in dependency order.

## 1. Fact Gathering Before Questioning
Finding facts from the repository or environment is the agent's job, never the user's:
1. Inspect existing project manifests (`pyproject.toml`, `package.json`, `CMakeLists.txt`, `environment.yml`), local `AGENTS.md` files, source interfaces, schemas, and test suites before asking any question.
2. Map the **decision tree**: identify which architectural choices are root prerequisites (such as data ownership, module boundaries, or execution model) and which downstream choices depend on those answers.

## 2. Audit Across Four Core Engineering Dimensions
Evaluate the proposed design against the architectural invariants in `~/.gemini/GEMINI.md` and the repository's `AGENTS.md`:

| Dimension | Key Questions to Stress-Test |
| :--- | :--- |
| **1. Boundaries & Dependency Injection** | Does the design keep pure domain/business logic separate from CLI wrappers, I/O, serialization, and network transport? Are external capabilities (clocks, filesystems, clients, sessions) injected explicitly without globals or singletons? |
| **2. Contracts, Lifetimes & Failure Modes** | Are input/output types, schemas, and ownership semantics explicit? How are invalid inputs, partial failures, resource cleanup, and concurrency hazards handled? |
| **3. Environment & Toolchain Fit** | Do builds, virtual/Conda environments, and scratch directories follow the active environment boundary (native WSL2 `ext4` `/home/<user>/...` without `/mnt/` bottlenecks when using WSL2, or local project directories on standalone Windows)? Does the design respect stack-specific rules when working in C++23 or PySpark repos? |
| **4. Verification & Rollback Strategy** | Can every behavior and edge case be proved with a fast, deterministic automated test (`pytest`, `unittest`, `ctest`, `npm test`), and can the change be reverted cleanly? |

## 3. Execute Frontier Interview Rounds
When one or more architectural trade-offs require user direction:
1. **Select the Active Frontier**:
   - Gather only the unresolved decisions whose prerequisites are already settled. Hold downstream questions that depend on open answers for a later round.
2. **Ask Structured Questions (`ask_question`)**:
   - Present 2 to 4 concrete options per question using the `ask_question` tool.
   - Place the recommended engineering option first, prefixed with `(Recommended)`, and state the concrete trade-off (complexity, latency, memory footprint, or failure mode) in each option.
3. **Advance the Tree**:
   - Once the user responds, update the design constraints, recompute the frontier, and ask the next round of newly unblocked questions.
   - Do not write implementation code until the decision frontier is empty, every module boundary and failure mode is locked, and the user confirms shared understanding.

## 4. Conclude with a Locked Contract Summary
Output a compact specification (under 10 lines) before starting implementation (or before invoking `/cxx-tdd-loop` or `/pyspark-tdd-loop` on specialized stacks):
- **Module Boundary**: Target files (`file://` links) and injected dependencies.
- **Data / Type Contract**: Key function/type signatures or schemas and error contracts.
- **Verification Gate**: The exact test or check command that will prove correctness.
