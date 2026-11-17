# Agent Toolkit

Configuration, global directives, cross-stack engineering skills, and specialized stack runbooks for Google Antigravity across **WSL2 + Windows (hybrid)**, **WSL2-only**, or **standalone Windows** environments.

## Architecture Overview

`agent-toolkit` separates universal engineering behavior from environment-specific boundaries and stack-specific execution loops:
- **Target-Aware Global Directives (`GEMINI.md`)**: Concatenates shared `directives/*.md` (`gemini-persona.md` -> `stack-standards.md` -> `safety-guidelines.md`) with the target environment policy (`directives/targets/wsl.md` for `both` / `wsl`, or `directives/targets/windows.md` for `windows`) into `<gemini_root>/GEMINI.md` without duplicating them inside `config/rules/`.
- **Universal Core Skills (`skills/shared/`)**: Stack-agnostic runbooks for dependency/tool evaluation (`research-first`), dependency-tree architecture reviews (`design-review`), technical documentation (`tech-docs`), prose/comment sanitization (`humanize`), and multi-profile project scaffolding (`scaffold-project`, which generates per-repo `AGENTS.md` files).
- **On-Demand Stack Packs (`skills/gemini/`)**: Specialized Red-Green-Refactor TDD loops and reference blueprints (`cxx-tdd-loop` for C++23/CMake 3.28+ and `pyspark-tdd-loop` for Conda/PySpark) that load only when triggered or referenced by a project's `AGENTS.md`.
- **Cross-OS Synchronization & Verification**: `deploy/deploy.py` is a thin CLI over `deploy/core/` (`targets.py`, `permissions.py`, `sync.py`, and `verify.py`). It supports `--target {both,windows,wsl}` (default `both`) and `--profile {all,core}`, merges OS-specific `globalPermissionGrants` templates into `config.json`, prunes stale rules/skills on request, and verifies `SKILL.md` frontmatter, repo/deployed links, ASCII punctuation, AI buzzwords, and zero deployment drift.

## Repository Layout

```text
agent-toolkit/
├── .agents/
│   └── skills.json                            # Workspace skill discovery registration
├── .gitattributes                             # Enforces LF line endings across WSL2 and Windows
├── configs/
│   ├── antigravity-wsl-template.json          # WSL2 globalPermissionGrants allow/ask/deny template
│   └── antigravity-windows-template.json      # Windows globalPermissionGrants allow/ask/deny template
├── deploy/
│   ├── __init__.py                            # Deploy package marker
│   ├── deploy.py                              # Thin CLI entrypoint and argument parser
│   └── core/
│       ├── __init__.py                        # Core subpackage marker
│       ├── permissions.py                     # Permission template loading, merge & safety checks
│       ├── sync.py                            # Directive build, skill copy & safe pruning
│       ├── targets.py                         # WSL2/Windows target & path resolution
│       └── verify.py                          # Repo hygiene, path link & drift verifier
├── directives/
│   ├── gemini-persona.md                      # Engineering posture, DI & 4-gate protocol
│   ├── stack-standards.md                     # Modular code standards, typing & stack dispatch
│   ├── safety-guidelines.md                   # Git rollback, PR review & secret isolation
│   └── targets/
│       ├── wsl.md                             # Hybrid WSL2 + Windows execution & mount boundaries
│       └── windows.md                         # Standalone Windows PowerShell & path boundaries
├── skills/
│   ├── gemini/
│   │   ├── cxx-tdd-loop/
│   │   │   ├── SKILL.md                       # C++23 + Ninja + CTest Red-Green-Refactor loop
│   │   │   └── references/
│   │   │       └── cxx23-cmake-blueprint.md   # Target-centric CMake 3.28+, C++23, -Werror & ASan/UBSan
│   │   └── pyspark-tdd-loop/
│   │       ├── SKILL.md                       # Conda + PySpark 5-gate Red-Green-Refactor loop
│   │       └── references/
│   │           └── pyspark-conda-blueprint.md # conda-forge environment.yml, StructType & Spark fixture
│   └── shared/
│       ├── design-review/SKILL.md             # Dependency-tree architectural frontier review
│       ├── humanize/
│       │   ├── SKILL.md                       # Engineering prose & code comment sanitizer
│       │   └── scripts/
│       │       └── check_content.py           # Standalone dash, quote & buzzword scanner (--fix)
│       ├── research-first/SKILL.md            # Built-in & open-source evaluation (Adopt, Wrap, Build)
│       ├── scaffold-project/SKILL.md          # Multi-stack project bootstrapper + per-repo AGENTS.md
│       └── tech-docs/SKILL.md                 # Diataxis result-first documentation & runbook standard
├── AGENTS.md                                  # Operational rules for agents editing this repository
└── README.md
```

## CLI Usage

Run from the repository root in WSL2 `bash` (or PowerShell on standalone Windows using `python`):

```bash
# 1. Preview planned deployment actions (both WSL2 and Windows by default) without writing
python3 deploy/deploy.py --dry-run --prune --sync-permissions

# 2. Deploy directives, all skills, and OS-specific permissions to both WSL2 and Windows Host
python3 deploy/deploy.py --sync-permissions

# 3. Deploy to WSL2 only (no Windows target checks or writes)
python3 deploy/deploy.py --target wsl --sync-permissions

# 4. Deploy to standalone Windows only (PowerShell-compatible directives + Windows permissions)
python deploy\deploy.py --target windows --sync-permissions

# 5. Deploy only generalized core skills (skills/shared/) without stack-specific packs
python3 deploy/deploy.py --profile core --sync-permissions

# 6. Prune stale rules/skills only after inspecting --dry-run --prune output and confirming
python3 deploy/deploy.py --prune --sync-permissions

# 7. Verify frontmatter, repo/deployed links, ASCII punctuation, buzzwords, and zero drift
python3 deploy/deploy.py --check --sync-permissions

# 8. Verify repository checks only (for CI or read-only sandboxes)
python3 deploy/deploy.py --check --repo-only

# 9. Auto-replace Unicode dashes/smart quotes and verify repo checks
python3 deploy/deploy.py --check --repo-only --fix
```

### Custom Target Overrides

If your WSL2 distribution name or Windows username differs from the auto-detected defaults:

```bash
python3 deploy/deploy.py --wsl-distro Ubuntu-24.04 --win-user <windows_username>
```
