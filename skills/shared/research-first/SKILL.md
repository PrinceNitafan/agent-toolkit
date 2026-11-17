---
name: research-first
description: "Evaluate built-in capabilities, official skills and plugins, and maintained open-source candidates before introducing a new dependency, tool, skill, MCP server, or system architecture. Weighs native fit, footprint, quality, cost, and supply-chain security, ending with an Adopt, Wrap, or Build decision. Trigger with /research-first."
---

# Research Before Building (`/research-first`)

Goal: avoid reinventing what the standard library, runtime built-ins, official platform tools, or a lean, maintained open-source package already solve cleanly, while preventing bloated or unsafe dependencies from entering the project.

## 1. Define the Capability & Constraints
State in 2 to 3 lines:
- What problem the component, tool, or workflow must solve and which module boundary owns it.
- Hard constraints: target OS/shell execution (WSL2 Linux or native Windows), runtime/language compatibility, dependency footprint, latency/memory bounds, or cost/licensing limits.

## 2. Search in Strict Priority Order
Always check what is already built into the runtime or platform before searching external registries:

| Priority | Scope | Where to Check First | What to Verify |
| :--- | :--- | :--- | :--- |
| **1. Built-in / Standard** | Language & Runtime | Standard library (`python` stdlib, Node/TS built-ins, C++23 `<expected>`/`<ranges>`/`<span>`, or native query engines like PySpark Catalyst) | Can ~50 lines of standard code replace an external package? |
| **1. Built-in / Platform** | Agent & Tooling | Official docs, Antigravity built-in skills, `search_marketplace`, Official MCP Registry (`registry.modelcontextprotocol.io`) | Does an official skill, plugin, or first-party tool already cover the workflow? |
| **2. Vetted Ecosystems** | Package Registries | Primary ecosystem registries (`PyPI`, `conda-forge`, `npm`, modern CMake packages) and curated MCP/Action directories | Maintainer identity, transitive dependency count, and clean integration with the repo's environment manager (`uv`, `conda`, `npm`, `CMake`). |
| **3. Primary Source** | GitHub / Upstream | Upstream repo (`gh search repos` / `gh search code`), build/manifest files, issue tracker, independent benchmarks | Last commit date, license, open issues, and benchmark methodology (repository stars are a weak signal). |

Record the research date and the exact version tag or commit SHA inspected. Do not recommend libraries from unverified memory. Label vendor-published benchmarks as vendor numbers, and for long-lived core tooling or architectural choices compare at least three independent sources and call out disagreements.

## 3. Vet Candidates Against Stack & Safety Rules
A directory or registry listing is not a security audit. Before shortlisting any external candidate, inspect its source and manifest files:
1. **Footprint & Modular Isolation**:
   - How much code and how many transitive dependencies does it pull in?
   - Can it be wrapped behind a narrow first-party interface or config so third-party types do not leak across every module?
2. **Toolchain & Runtime Hygiene**:
   - Does it install and run cleanly in the active environment (WSL2 Linux or native Windows) with the project's declared toolchain (`uv`/`pyproject.toml`, `npm`/`package.json`, `conda`/`environment.yml`, or `CMake`/`Ninja` without disabling `-Werror`)?
3. **Supply Chain, Permissions & License Check**:
   - Confirm a permissive or compatible license (MIT, BSD, Apache-2.0, BSL-1.0), active maintenance, and an immutable release tag or commit SHA to pin (per `~/.gemini/GEMINI.md`, Third-Party Code & Tooling Hygiene).
   - For MCP servers, hooks, GitHub Actions, and third-party skills, inspect what shell commands, network calls, and repository or token permissions they require. Prefer copying a small, auditable module you have read over running an opaque third-party installer.

## 4. Compare Candidates & Decide (Adopt, Wrap, or Build)
Compare the top 2 to 3 options across four criteria:
- **Native Fit**: Standard library / built-in coverage vs external code.
- **Footprint & Cost**: Dependency size, build/startup impact, and any service cost against the current baseline.
- **Quality & Performance**: Correctness evidence, resource control, and test coverage.
- **Maintenance & Security**: Commit activity, permission scope, license, and SHA pinning.

Conclude with a 2 to 4 line decision (with links and the research date):
- **Adopt**: Use the built-in capability or drop-in tool directly.
- **Wrap**: Pull the external package (pinned to a tag/SHA) and isolate it behind an explicit dependency-injected interface.
- **Build**: Write a focused first-party implementation when external options are bloated, unmaintained, unsafe, or incompatible with project constraints.

If two options have close trade-offs or one introduces a paid service, pause and ask the user with `ask_question` (recommended option first).

## 5. When to Skip
Skip this runbook for localized bug fixes, routine TDD iterations inside an existing module, or when the user has already specified the exact library or tool to use.
