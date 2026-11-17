"""Target discovery and cross-OS path resolution for WSL2 and Windows."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from deploy.core.permissions import PERMISSION_TEMPLATES

TARGET_CHOICES: tuple[str, ...] = ("both", "windows", "wsl")

# Built-in Windows profile folders skipped when auto-detecting the host username under /mnt/c/Users.
SYSTEM_WIN_USERS: frozenset[str] = frozenset({
    "All Users",
    "Administrator",
    "Default",
    "Default User",
    "DefaultAccount",
    "Guest",
    "Public",
    "WDAGUtilityAccount",
    "defaultuser0",
})


@dataclass(frozen=True)
class SyncTarget:
    """Resolved Antigravity deployment destination and its environment templates."""

    name: str
    gemini_root: Path
    directive_target: str
    permission_template: str
    home_dir: str | None = None
    skip_if_unmounted: bool = False
    mount_root: Path | None = None
    require_existing_home: bool = False


def validate_segment(label: str, value: str) -> str:
    """Reject empty or path-traversal values for user and distro identifiers."""
    stripped = value.strip()
    if not stripped or stripped in {".", ".."} or any(sep in value for sep in ("/", "\\", "\0")):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def _safe_exists(path: Path) -> bool:
    """Probe path existence while treating inaccessible/unmounted cross-OS errors as False."""
    try:
        return path.exists()
    except OSError:
        return False


def target_mount_probe(target: SyncTarget) -> Path:
    """Return the path checked to distinguish an unmounted cross-OS host from a missing user."""
    return target.mount_root if target.mount_root is not None else target.gemini_root.parent


def is_unmounted_target(target: SyncTarget) -> bool:
    """Return True when an optional cross-OS target mount root is not reachable."""
    return (
        target.skip_if_unmounted
        and not _safe_exists(target.gemini_root)
        and not _safe_exists(target_mount_probe(target))
    )


def windows_home_from_root(win_root: Path, platform: str | None = None) -> str:
    """Return the native Windows home directory for template substitution."""
    active_platform = sys.platform if platform is None else platform
    parent = Path(os.path.abspath(win_root)).parent
    if active_platform == "win32":
        return str(parent).rstrip("\\/")

    parts = parent.parts
    if (
        len(parts) >= 3
        and parts[0] == "/"
        and parts[1] == "mnt"
        and len(parts[2]) == 1
        and parts[2].isalpha()
    ):
        drive = parts[2].upper()
        tail = "\\".join(parts[3:])
        return f"{drive}:\\{tail}" if tail else f"{drive}:"
    return parent.as_posix().rstrip("/")


def target_home_dir(target: SyncTarget) -> str:
    """Return the home directory for template substitution."""
    raw = target.home_dir if target.home_dir is not None else target.gemini_root.parent.as_posix()
    return raw.rstrip("/\\")


def detect_win_user(fallback: str, users_dir: Path = Path("/mnt/c/Users")) -> str:
    """Resolve the Windows host username when WSL2 and Windows usernames differ."""
    try:
        if not users_dir.is_dir() or (users_dir / fallback).is_dir():
            return fallback
        candidates = [
            d.name
            for d in sorted(users_dir.iterdir())
            if d.is_dir() and d.name not in SYSTEM_WIN_USERS and not d.name.startswith(".")
        ]
    except OSError:
        return fallback
    return candidates[0] if len(candidates) == 1 else fallback


def _resolve_windows_target(
    *,
    mode: str,
    directive_env: str,
    wsl_user: str,
    win_user: str | None,
    windows_gemini_dir: Path | None,
    active_platform: str,
    win_users_dir: Path,
) -> SyncTarget:
    resolved_user = win_user or (
        wsl_user if active_platform == "win32" else detect_win_user(wsl_user, users_dir=win_users_dir)
    )
    if windows_gemini_dir is not None:
        win_root = windows_gemini_dir
    elif active_platform == "win32" and sys.platform == "win32" and win_user is None:
        # Respect %USERPROFILE% on native Windows (handles custom drives and domain profile names).
        win_root = Path.home() / ".gemini"
    elif active_platform == "win32":
        win_root = Path(f"C:/Users/{resolved_user}/.gemini")
    else:
        win_root = win_users_dir / resolved_user / ".gemini"
    # Skip only when Windows is an optional secondary target in 'both' mode and not explicitly overridden.
    win_skip = (
        active_platform != "win32"
        and mode == "both"
        and windows_gemini_dir is None
        and win_user is None
    )
    require_home = windows_gemini_dir is None and (
        active_platform != "win32" or win_user is not None
    )
    return SyncTarget(
        name=f"Windows Host ({resolved_user})",
        gemini_root=win_root,
        directive_target=directive_env,
        permission_template=PERMISSION_TEMPLATES["windows"],
        home_dir=windows_home_from_root(win_root, platform=active_platform),
        skip_if_unmounted=win_skip,
        mount_root=win_users_dir if win_skip else None,
        require_existing_home=require_home,
    )


def _resolve_wsl_target(
    *,
    mode: str,
    directive_env: str,
    wsl_distro: str,
    wsl_user: str,
    wsl_gemini_dir: Path | None,
    active_platform: str,
) -> SyncTarget:
    if active_platform == "win32":
        if wsl_gemini_dir is not None:
            wsl_root = wsl_gemini_dir
        else:
            # Windows 10/11 exposes WSL filesystems via \\wsl$ or \\wsl.localhost depending on build.
            unc = Path(rf"\\wsl$\{wsl_distro}\home\{wsl_user}\.gemini")
            alt = Path(rf"\\wsl.localhost\{wsl_distro}\home\{wsl_user}\.gemini")
            use_alt = not _safe_exists(unc.parent) and _safe_exists(alt.parent)
            wsl_root = alt if use_alt else unc
        wsl_home = f"/home/{wsl_user}"
        wsl_skip = mode == "both" and wsl_gemini_dir is None
        mount_root = wsl_root.parent.parent if wsl_skip else None
        require_home = wsl_gemini_dir is None
    else:
        wsl_root = wsl_gemini_dir or Path(f"/home/{wsl_user}/.gemini")
        wsl_home = Path(os.path.abspath(wsl_root)).parent.as_posix().rstrip("/")
        wsl_skip = False
        mount_root = None
        require_home = False

    return SyncTarget(
        name=f"WSL2 ({wsl_distro}:{wsl_user})",
        gemini_root=wsl_root,
        directive_target=directive_env,
        permission_template=PERMISSION_TEMPLATES["wsl"],
        home_dir=wsl_home,
        skip_if_unmounted=wsl_skip,
        mount_root=mount_root,
        require_existing_home=require_home,
    )


def resolve_targets(
    *,
    mode: str,
    wsl_user: str,
    wsl_distro: str = "Ubuntu",
    win_user: str | None = None,
    windows_gemini_dir: Path | None = None,
    wsl_gemini_dir: Path | None = None,
    platform: str | None = None,
    win_users_dir: Path = Path("/mnt/c/Users"),
) -> list[SyncTarget]:
    """Resolve concrete Windows and/or WSL2 Antigravity deployment targets."""
    if mode not in TARGET_CHOICES:
        raise ValueError(f"Unsupported target mode '{mode}'; expected one of {TARGET_CHOICES}")
    validate_segment("wsl_user", wsl_user)
    validate_segment("wsl_distro", wsl_distro)
    if win_user is not None:
        validate_segment("win_user", win_user)

    active_platform = sys.platform if platform is None else platform
    directive_env = "windows" if mode == "windows" else "wsl"
    targets: list[SyncTarget] = []

    if mode in ("both", "windows"):
        targets.append(
            _resolve_windows_target(
                mode=mode,
                directive_env=directive_env,
                wsl_user=wsl_user,
                win_user=win_user,
                windows_gemini_dir=windows_gemini_dir,
                active_platform=active_platform,
                win_users_dir=win_users_dir,
            )
        )

    if mode in ("both", "wsl"):
        targets.append(
            _resolve_wsl_target(
                mode=mode,
                directive_env=directive_env,
                wsl_distro=wsl_distro,
                wsl_user=wsl_user,
                wsl_gemini_dir=wsl_gemini_dir,
                active_platform=active_platform,
            )
        )

    return targets
