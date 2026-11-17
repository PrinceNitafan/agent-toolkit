#!/usr/bin/env python3
"""CLI entrypoint for syncing and verifying agent-toolkit directives, skills, and permissions."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

# Allow `python3 deploy/deploy.py` execution from any working directory without PYTHONPATH=.
if __package__ in (None, ""):
    _repo_parent = str(Path(__file__).resolve().parent.parent)
    if not sys.path or sys.path[0] != _repo_parent:
        sys.path.insert(0, _repo_parent)

from deploy.core.sync import PROFILE_CHOICES, sync_target  # noqa: E402
from deploy.core.targets import (  # noqa: E402
    TARGET_CHOICES,
    SyncTarget,
    is_unmounted_target,
    resolve_targets,
    target_mount_probe,
)
from deploy.core.verify import check_drift, check_repo  # noqa: E402


def build_parser(default_user: str) -> argparse.ArgumentParser:
    """Build the CLI argument parser for deployment and verification."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--target",
        choices=TARGET_CHOICES,
        default="both",
        help="Environment(s) to sync or check: 'both' (hybrid WSL2 + Windows), 'windows', or 'wsl'.",
    )
    parser.add_argument("--wsl-distro", default="Ubuntu")
    parser.add_argument("--wsl-user", default=default_user)
    parser.add_argument("--win-user")
    parser.add_argument("--windows-gemini-dir", type=Path)
    parser.add_argument("--wsl-gemini-dir", type=Path)
    parser.add_argument(
        "--profile",
        choices=PROFILE_CHOICES,
        default="all",
        help="Skill profile to deploy: 'all' (shared + stack packs) or 'core' (shared only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deployment actions without writing.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify frontmatter, links, content, and drift.",
    )
    parser.add_argument(
        "--repo-only",
        action="store_true",
        help="With --check, skip deployed target checks.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="With --check, replace Unicode dashes and smart quotes.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove stale files in config/rules and config/skills.",
    )
    parser.add_argument(
        "--sync-permissions",
        action="store_true",
        help="Merge target permission template(s) into config.json.",
    )
    return parser


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Path:
    """Validate CLI flag combinations and ensure --repo-root exists before side effects."""
    if args.dry_run and args.check:
        parser.error("--dry-run cannot be combined with --check")
    if args.repo_only and not args.check:
        parser.error("--repo-only requires --check")
    if args.fix and not args.check:
        parser.error("--fix requires --check")
    if args.prune and args.check:
        parser.error("--prune cannot be combined with --check")

    repo_root = args.repo_root.resolve()
    if not repo_root.is_dir():
        parser.error(f"--repo-root is not an existing directory: {repo_root}")
    return repo_root


def run_checks(repo_root: Path, targets: list[SyncTarget], args: argparse.Namespace) -> int:
    """Run repository checks and optional deployed target drift checks."""
    issues = check_repo(repo_root, fix=args.fix)
    if not args.repo_only:
        for target in targets:
            if is_unmounted_target(target):
                print(f"[SKIP] {target.name} ({target_mount_probe(target)} not mounted)")
                continue
            issues.extend(
                check_drift(repo_root, target, args.sync_permissions, args.profile)
            )

    for item in issues:
        print(f"[FAIL] {item}")
    scope = "repo checks" if args.repo_only else "all checks"
    print(f"OK: {scope} passed." if not issues else f"Failed with {len(issues)} issue(s).")
    return 1 if issues else 0


def run_deploy(repo_root: Path, targets: list[SyncTarget], args: argparse.Namespace) -> int:
    """Deploy directives, skills, and optional permissions across all resolved targets."""
    # Attempt every target even if an earlier target fails so partial host issues do not block WSL2.
    results = [
        sync_target(
            repo_root,
            target,
            args.dry_run,
            args.sync_permissions,
            args.prune,
            args.profile,
        )
        for target in targets
    ]
    return 0 if all(results) else 1


def _default_user() -> str:
    """Resolve current OS username, falling back safely in stripped CI containers."""
    try:
        return getpass.getuser()
    except (ImportError, KeyError, OSError):
        return os.environ.get("USERNAME") or os.environ.get("USER") or "user"


def main(argv: list[str] | None = None) -> int:
    """Parse CLI options, resolve targets, and dispatch check or deployment mode."""
    parser = build_parser(default_user=_default_user())
    args = parser.parse_args(argv)
    repo_root = validate_args(parser, args)

    try:
        targets = resolve_targets(
            mode=args.target,
            wsl_user=args.wsl_user,
            wsl_distro=args.wsl_distro,
            win_user=args.win_user,
            windows_gemini_dir=args.windows_gemini_dir,
            wsl_gemini_dir=args.wsl_gemini_dir,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.check:
        return run_checks(repo_root, targets, args)
    return run_deploy(repo_root, targets, args)


if __name__ == "__main__":
    raise SystemExit(main())
