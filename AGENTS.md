# Workspace Instructions (`AGENTS.md`)

Operational rules for AI agents modifying `agent-toolkit`.

## 1. Repository Purpose & Layout
`agent-toolkit` manages global Antigravity (`~/.gemini` and `%USERPROFILE%\.gemini`) directives, cross-stack core skills, and on-demand stack packs across **WSL2 + Windows (hybrid)**, **WSL2-only**, or **standalone Windows** workstations.

| Path | Role | Deployed Destination (`<gemini_root>`) |
| :--- | :--- | :--- |
| `directives/` | Shared global directives (`gemini-persona.md`, `stack-standards.md`, `safety-guidelines.md`) plus `directives/targets/{wsl,windows}.md`. | Concatenated into `GEMINI.md` |
| `skills/shared/` | Stack-agnostic core skills (`research-first`, `design-review`, `scaffold-project`, `tech-docs`, `humanize`). | `config/skills/<skill-name>/` (`--profile all` or `core`) |
| `skills/gemini/` | On-demand stack TDD loops (`cxx-tdd-loop`, `pyspark-tdd-loop`) and `references/` blueprints. | `config/skills/<skill-name>/` (`--profile all`) |
| `configs/` | OS-specific Antigravity permission templates (`antigravity-wsl-template.json`, `antigravity-windows-template.json`; `{home}` expanded by `deploy/deploy.py`). | `config/config.json` (when `--sync-permissions` is passed) |
| `deploy/` | Thin CLI entrypoint (`deploy/deploy.py`) over `deploy/core/` (`targets.py`, `permissions.py`, `sync.py`, `verify.py`). | Not deployed (tooling) |

## 2. Hard Invariants for Edits
1. **Source-of-Truth Discipline**:
   - Edit files inside this repository (`directives/`, `skills/`, `configs/`, `deploy/`), never directly inside `~/.gemini/` or `/mnt/c/Users/<user>/.gemini/`.
   - Propagate changes by running `python3 deploy/deploy.py`.
   - Ask for explicit user confirmation after previewing `--dry-run --prune` before running `python3 deploy/deploy.py --prune`, because `--prune` deletes any entry in `config/rules/` or `config/skills/` not tracked in this repository.
2. **Strict ASCII, Frontmatter & Path Hygiene**:
   - Every `.md` file in this repository is checked by `python3 deploy/deploy.py --check`.
   - Never emit Unicode dashes (`U+2014`, `U+2013`, `U+2012`, `U+2015`, `U+2212`) or curly quotes (`U+2018` through `U+201D`) anywhere in markdown files, including inside code blocks.
   - Never use banned AI buzzwords in prose (`delve`, `tapestry`, `testament`, `landscape`, `pivotal`, `beacon`, `foster`, `streamline`, `dive deep`, `seamless`, `multifaceted`, `holistic`, `crucial`, `furthermore`, `moreover`, `it is important to note`, `it is worth noting`). When documenting a banned word as a rule example, wrap it in inline backticks (`` `word` ``).
   - Every `SKILL.md` must start with YAML frontmatter containing `name` (matching its folder name) and a non-empty `description`.
   - Every concrete repo-relative path (`directives/...`, `skills/...`, `deploy/...`) or skill-local `references/...` path mentioned in markdown must exist on disk. Inside `skills/`, reference deployed paths (`~/.gemini/GEMINI.md`, `~/.gemini/config/skills/...`) instead of repo-only `directives/...` or `skills/...` paths.
3. **Target Execution**:
   - Run verification and deployment commands in WSL2 `bash` (`python3 deploy/deploy.py ...`) or native Windows PowerShell (`python deploy\deploy.py --target windows ...`) depending on the active workstation mode.
4. **Guardrail Change Approval**:
   - Put changes to `configs/`, `directives/safety-guidelines.md`, or `deploy/` on a scoped branch and get explicit user approval before merging or deploying them into `<gemini_root>`.

## 3. Verification Commands
Run verification before finishing any change to `directives/`, `skills/`, `configs/`, or `deploy/`:

```bash
# Verify repo hygiene (frontmatter, paths, typography, buzzwords) without deployed targets
python3 deploy/deploy.py --check --repo-only

# Preview planned file sync (and any stale rule/skill pruning) without writing
python3 deploy/deploy.py --dry-run --prune --sync-permissions

# Auto-fix forbidden Unicode dashes and curly quotes, then deploy and verify zero drift
python3 deploy/deploy.py --check --repo-only --fix
python3 deploy/deploy.py --sync-permissions
python3 deploy/deploy.py --check --sync-permissions

# Only after inspecting --dry-run --prune output and getting user confirmation:
python3 deploy/deploy.py --prune --sync-permissions
```
