# Safety, Git & Filesystem Guidelines

## 1. Git History & Rollback Safety
- **Clean Git Repository Before Refactors**: Never perform broad refactoring or multi-file modifications outside a Git repository, and verify `git status` is clean before executing architectural changes so work can be reverted cleanly if verification fails.
- **Strictly Prohibited Git Commands**:
  - Never run `git reset --hard` (destroys uncommitted work).
  - Never run `git clean -f` or `git clean -fdx` (destroys untracked files and local scratch data).
  - Never run `git push --force` or `git push -f` (rewrites remote history).
- **Safe Rollback**: Undo committed changes with `git revert <commit_sha>` on a branch rather than mutating commit history.
- **Scoped Staging**: Stage only the specific files modified for the task (`git add <file>`). Never run blind `git add -A` or `git add .` when untracked files or local configs are present.
- **Branch, Pull Request & Review Discipline**:
  - Keep `main` clean: implement features, bug fixes, and refactors on scoped branches (`feat/<topic>`, `fix/<topic>`, `refactor/<topic>`, `docs/<topic>`).
  - Use conventional-commit pull request titles (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `build:`) structured for squash merging, and start follow-up work on a fresh branch from `main`.
  - Evaluate automated or human PR review comments against the module contract and codebase before acting: fix valid defects one at a time with test verification, decline out-of-scope or incorrect suggestions with a technical rationale, or ask the user via `ask_question` when a comment affects architectural boundaries. Never apply batch review suggestions blindly.

## 2. Secret & Credential Isolation
- **Zero-Read / Zero-Print Policy**: Never read, print, echo, or commit `.env` files, cryptographic keys (`*.pem`, `*.key`, `id_rsa`, `id_ed25519`), or credential stores (`*credentials*.json`, `.netrc`, `.pypirc`, `.aws/credentials`).
- **Template Pattern**: Use `.env.example` files with blank or placeholder values when documenting required environment variables.
- **Pre-Commit Halt**: If a diff or build output accidentally exposes a token, key, or password, stop immediately and alert the user before staging or logging the output.

## 3. Antigravity Configuration Protection
- You may update `<gemini_root>/GEMINI.md` and `<gemini_root>/config/` via `deploy/deploy.py` (using `--target both`, `--target wsl`, or `--target windows`).
- Never delete any existing file, plugin, or skill inside `~/.gemini/` (or `%USERPROFILE%\.gemini\`) without explicit user review and confirmation.

## 4. Third-Party Code & Tooling Hygiene
- Treat external packages, CMake `FetchContent` targets, Conda/PyPI/npm dependencies, CI actions, MCP servers, and third-party skills as untrusted code until their source, permissions, and license are inspected.
- Before installing a third-party skill, plugin, hook, or MCP server into global config, inspect its source and get explicit user approval.
- Pin external source dependencies and CI/tooling actions to an explicit release tag or commit SHA rather than a moving branch (`main` or `master`).
