# Environment & Filesystem Discipline (WSL2 / Hybrid Setup)

## 1. Execution Boundary (WSL2 + Windows Host)
- **Execution Boundary**: Operate in a hybrid architecture where Windows acts as the host UI and WSL2/Linux is the sole execution environment. Keep all source repositories, builds, test execution, and data processing inside the native WSL2 Linux filesystem (`/home/<username>/...`).
- **No Windows Shell Execution**: Never invoke build, environment, package-manager, linter, or test-runner tools (`python`, `python3`, `uv`, `pytest`, `conda`, `node`, `npm`, `cmake`, `ninja`, `g++`, `clang++`, `ctest`, `spark-submit`) through Windows PowerShell (`powershell.exe`, `pwsh.exe`) or `cmd.exe`. Run all build, environment, and runtime commands natively in WSL2 `bash`.
- **Automatic Windows-to-WSL2 Path Translation**:
  - Whenever given a Windows host path (for example, `C:\Users\...\file.txt` or `D:\datasets\raw.parquet`), translate it to its WSL2 mount equivalent (`/mnt/c/Users/.../file.txt` or `/mnt/d/datasets/raw.parquet`) before passing it to any Linux command, script, or file tool.
  - Normalize drive letters to lowercase under `/mnt/<drive>/`, convert backslashes (`\`) to forward slashes (`/`), or resolve paths programmatically with `wslpath -u '<win_path>'`.
- **Filesystem Placement Discipline**:
  - Keep active git repositories, build trees (`build/`, `dist/`), virtual/Conda environments, and local scratch directories on the native WSL2 `ext4` filesystem (`/home/<username>/...`) to avoid cross-OS `/mnt/` I/O bottlenecks.
  - Access `/mnt/c/` or `/mnt/d/` only when reading or exporting files explicitly located on the Windows host.

## 2. Host Mount & Recursive Deletion Protection
- **Hard-Denied Destructive Deletions**:
  - Never execute recursive deletion commands (`rm -rf`, `shutil.rmtree`, `find ... -delete`) targeting `/mnt/c/`, `/mnt/d/`, `~` (`/home/<username>`), or any parent directory above the active repository root.
  - When cleaning build or cache trees inside WSL2, scope removal strictly to the named directory inside the project (for example, `rm -rf ./build` after verifying `pwd` is the repository root) or prefer build-tool clean targets (`cmake --build build --target clean`).
- **Windows Mount Protection (`/mnt/c/`, `/mnt/d/`)**:
  - Treat Windows host user folders (`/mnt/c/Users/<win_user>/Desktop`, `Downloads`, `Documents`) as read-only inputs. Never modify or delete host files unless explicitly instructed by the user.
  - Treat personal media folders (`Pictures`, `Videos`, `Music`) and drive roots (`/mnt/c/`, `/mnt/d/`) as off-limits (no read, write, or delete) unless explicitly requested.
