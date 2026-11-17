---
name: scaffold-project
description: "Bootstrap a new Python 3.12 (uv/CLI), TypeScript/Node, C++23/CMake, or Conda/PySpark repository on native filesystem storage with tailored AGENTS.md rules, test fixtures, and Git initialization. Trigger with /scaffold-project."
---

# Project Repository Scaffolder (`/scaffold-project`)

Goal: initialize a clean, build-verified project repository on fast local storage (`/home/<username>/...` on WSL2 `ext4`, or a local drive path on standalone Windows) with a project-scoped `AGENTS.md` so stack-specific rules live with the repository rather than polluting global instructions.

## 1. Validate Target Path & Profile
1. **Enforce Native Storage Placement**:
   - In WSL2/hybrid setups, confirm the target parent directory resides under `/home/<username>/...` (never under `/mnt/c/` or `/mnt/d/`). On standalone Windows, use a local directory outside `Desktop`, `Downloads`, or `Documents`.
   - Verify the target project directory does not already exist or is empty before writing files.
2. **Select Stack Profile**:
   - Choose one profile from the request (`python-cli`, `ts-node`, `cxx23-cmake`, or `pyspark-conda`).
   - If the user has not specified which stack profile to scaffold, ask with `ask_question` (listing the recommended profile first).

## 2. Generate Profile Layout & Project `AGENTS.md`
Every profile must generate a root `AGENTS.md` documenting that repository's module boundaries, environment/toolchain rules, and exact build, lint, and test verification commands.

### Profile A: `python-cli` (Python 3.12+ + `uv` / `pyproject.toml` + `pytest` + `ruff` + `mypy`)
Create the following tree:
- `pyproject.toml`:
  - `requires-python = ">=3.12"`, `pytest` (`testpaths = ["tests"]`), `ruff` (`line-length = 100`), and `mypy` (`python_version = "3.12"`, `strict = true`).
- `src/<package>/cli.py` (thin `argparse` entrypoint shell) separated from `src/<package>/core.py` (pure typed domain functions).
- `tests/test_core.py` with a passing unit test.
- `AGENTS.md` locking `uv run pytest`, `uv run ruff check .`, and `uv run mypy src tests` (or `python3 -m unittest` when stdlib-only).
- `.env.example`, `README.md`, and `.gitignore` (ignoring `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `dist/`, `.env`).

### Profile B: `ts-node` (TypeScript + Node.js LTS + Strict `tsconfig.json`)
Create the following tree:
- `package.json` (`"type": "module"`, scripts for `build`, `check`, and `test`) and `tsconfig.json` (`"strict": true`, `"noUncheckedIndexedAccess": true`).
- `src/index.ts` (pure typed module) and `tests/index.test.ts` (using Node's built-in `node --test` runner or Vitest).
- `AGENTS.md` locking strict TypeScript checking (`npx tsc --noEmit`) and test execution (`npm test`).
- `.env.example`, `README.md`, and `.gitignore` (ignoring `node_modules/`, `dist/`, `.env`).

### Profile C: `cxx23-cmake` (C++23 + CMake 3.28+ + Ninja + GTest)
Create the following tree (see `~/.gemini/config/skills/cxx-tdd-loop/references/cxx23-cmake-blueprint.md`):
- `CMakeLists.txt`:
  - `cmake_minimum_required(VERSION 3.28)`, `CMAKE_CXX_STANDARD 23`, `CMAKE_CXX_STANDARD_REQUIRED ON`, `CMAKE_CXX_EXTENSIONS OFF`, `CMAKE_EXPORT_COMPILE_COMMANDS ON`.
  - Interface target `project_warnings` with `-Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion -Wshadow -Wnon-virtual-dtor -Wold-style-cast -Werror`.
  - Core static library target and `GTest::gtest_main` test executable registered via `enable_testing()` and `add_test()`.
- `CMakePresets.json`:
  - `debug-asan`: Ninja generator, `CMAKE_BUILD_TYPE=Debug`, `ENABLE_SANITIZERS=ON` (`-fsanitize=address,undefined -fno-omit-frame-pointer`).
  - `release`: Ninja generator, `CMAKE_BUILD_TYPE=Release`, `ENABLE_SANITIZERS=OFF`.
- `include/<project>/`, `src/`, and `tests/` with a minimal header contract, implementation stub, and passing GTest smoke test.
- `AGENTS.md` instructing agents to activate `/cxx-tdd-loop` (`~/.gemini/config/skills/cxx-tdd-loop/SKILL.md`) and enforce zero warnings and ASan/UBSan checks.
- `.clang-format`, `README.md`, and `.gitignore` (ignoring `build/`, `build-*/`, `compile_commands.json`, `.env`).

### Profile D: `pyspark-conda` (Conda + PySpark + PyArrow + `pytest`)
Create the following tree (see `~/.gemini/config/skills/pyspark-tdd-loop/references/pyspark-conda-blueprint.md`):
- `environment.yml`:
  - Channels: `conda-forge`, `nodefaults`.
  - Dependencies: `python=3.12`, `openjdk=17`, `pyspark=3.5.*`, `pyarrow>=15.0`, `pandas>=2.2`, `pytest>=8.0`, `ruff`, `mypy`.
- `pyproject.toml`:
  - `pytest` (`testpaths = ["tests"]`), `ruff` (`line-length = 100`), and `mypy` (`python_version = "3.12"`, `strict = true`).
- `src/<package>/__init__.py` and `src/<package>/schemas.py` with an explicit `StructType` example contract.
- `tests/conftest.py` providing a session-scoped `spark` fixture (`master("local[2]")`, `spark.sql.shuffle.partitions=2`, `spark.ui.enabled=false`, `spark.local.dir` on local `tmp_path_factory`).
- `AGENTS.md` instructing agents to activate `/pyspark-tdd-loop` (`~/.gemini/config/skills/pyspark-tdd-loop/SKILL.md`) and enforce explicit `StructType` schemas and `conda run -n <env_name> pytest`.
- `.env.example`, `README.md`, and `.gitignore` (ignoring `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `spark-warehouse/`, `metastore_db/`, `derby.log`, `.env`).

## 3. Initialize Git & Run Verification
1. Initialize the repository on `main`:
   ```bash
   git -C <project_dir> init -b main
   ```
2. Run the stack verification check in the active environment shell:
   - `python-cli`: `uv run pytest` (or `python3 -m unittest discover -s tests` for stdlib-only projects).
   - `ts-node`: `npm test`.
   - `cxx23-cmake`: `cmake --preset debug-asan && cmake --build --preset debug-asan && ctest --preset debug-asan --output-on-failure` (or `cmake -B build -G Ninja` if presets are not invoked).
   - `pyspark-conda`: `conda run -n <env_name> pytest`.
3. Output a concise report (under 8 lines) with `file://` links to the generated root files (`AGENTS.md`, manifest, and tests) and the verification command result.
