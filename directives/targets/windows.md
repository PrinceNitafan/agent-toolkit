# Environment & Filesystem Discipline (Standalone Windows)

## 1. Execution Boundary (Native Windows)
- **Execution Shell**: Execute builds, package managers, linters, and test suites natively in Windows PowerShell (`pwsh` / `powershell.exe`) using native Windows paths (`C:\Users\<username>\...`) and virtual or Conda environments.
- **Tooling Parity**: Use `python` / `py -3`, `uv`, `pytest`, `conda`, `node`, `npm`, `cmake`, `ninja`, and `ctest` directly on Windows without assuming WSL2 mounts (`/mnt/c/`), `wslpath`, or Linux `/home/` directories exist.
- **Line Endings & Encoding**: Keep repository text files normalized to LF (`* text=auto eol=lf` when `.gitattributes` is present) and UTF-8 without BOM.

## 2. Windows System & Profile Protection
- **Hard-Denied Destructive Deletions**:
  - Never execute recursive deletion commands (`Remove-Item -Recurse -Force`, `rmdir /s /q`, `del /f /s /q`, `shutil.rmtree`) targeting drive roots (`C:\`, `D:\`), `%USERPROFILE%`, system directories, or any parent directory above the active repository root.
  - When cleaning build or cache trees, scope removal strictly to the named subdirectory inside the repository (for example, `Remove-Item -Recurse -Force .\build` after verifying the current working directory is the repository root) or use build-tool clean targets (`cmake --build build --target clean`).
- **Protected Windows Folders**:
  - Treat `C:\Windows\`, `C:\Program Files\`, and `C:\Program Files (x86)\` as read-only system boundaries. Never write to or delete inside them.
  - Treat user profile folders (`Desktop`, `Downloads`, `Documents`) as read-only inputs and personal media folders (`Pictures`, `Videos`, `Music`) as off-limits unless explicitly instructed by the user.
