# Technical Stack & Modular Standards

## 1. Code Quality & Modular Architecture
- **Pure Core vs I/O Shell**: Keep CLI argument parsing, HTTP handlers, and filesystem/database I/O in a thin entrypoint layer, separate from pure domain and validation functions that accept value types or `pathlib.Path` so they can be unit-tested without subprocesses or live network calls.
- **Explicit Typing & Validation**:
  - Require explicit type annotations across all functions, public interfaces, and data models.
  - Validate untrusted external inputs, configurations, and required environment variables at startup (fail-fast) before executing side effects.
- **Lean & Surgical Changes**:
  - Write the minimum code that solves the request. Avoid single-use abstractions, speculative configuration flags, or handling for impossible states.
  - Follow language naming conventions consistently (`snake_case` in Python/C++, `camelCase` in TypeScript) and match the surrounding style of the repository.

## 2. Toolchain & Stack Conventions
- **Python 3.12+**:
  - Respect the repository's declared environment manager: use `uv` (or standard `venv` with `pyproject.toml`) for standalone CLIs, services, and AI tooling; use `conda` (`environment.yml`) when managing JVM/PySpark or binary C-extension stacks.
  - Never install packages into the system Python or global `base` environment.
  - Verify static types with `mypy` or `pyright`, format/lint with `ruff`, and test with `pytest` (or `unittest` for stdlib-only scripts).
- **TypeScript / Node.js**:
  - Target Node.js LTS with strict TypeScript (`strict: true` in `tsconfig.json`) for web, frontend, and Node tooling.
- **Specialized Systems & Data Stacks (On-Demand Dispatch)**:
  - Do not enforce C++23/CMake or PySpark/Conda rules in general repositories.
  - When working in a C++23/CMake repository, activate `/cxx-tdd-loop` (`~/.gemini/config/skills/cxx-tdd-loop/SKILL.md`) to enforce `-std=c++23`, target-centric CMake 3.28+, `-Werror`, and ASan/UBSan verification.
  - When working in a Conda/PySpark data pipeline, activate `/pyspark-tdd-loop` (`~/.gemini/config/skills/pyspark-tdd-loop/SKILL.md`) to enforce explicit `StructType` schemas, Catalyst/Arrow transformations, and injected `SparkSession` fixtures.
  - Always check the repository's root `AGENTS.md` for project-specific build, lint, and test gates.

