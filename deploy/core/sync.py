"""Directive compilation, skill discovery, pruning, and target synchronization."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from deploy.core.permissions import format_config_json, load_json, merge_permission_grants
from deploy.core.targets import SyncTarget, is_unmounted_target, target_home_dir, target_mount_probe

# Concatenation order for <gemini_root>/GEMINI.md; unlisted *.md files append alphabetically.
DIRECTIVE_PRIORITY: tuple[str, ...] = (
    "gemini-persona.md",
    "stack-standards.md",
    "safety-guidelines.md",
)
PROFILE_SCOPES: dict[str, tuple[str, ...]] = {
    "all": ("shared", "gemini"),
    "core": ("shared",),
}
PROFILE_CHOICES: tuple[str, ...] = tuple(PROFILE_SCOPES)
SKILL_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".*")


def write_lf_text(path: Path, content: str) -> None:
    """Write UTF-8 text with LF line endings regardless of host OS."""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def norm_text(text: str) -> str:
    """Normalize CRLF/LF endings so cross-OS drift checks compare content only."""
    return text.replace("\r\n", "\n").strip()


def files_match(src: Path, dst: Path) -> bool:
    """Compare source and destination files, falling back to bytes for binary assets."""
    try:
        return norm_text(src.read_text(encoding="utf-8")) == norm_text(dst.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return src.read_bytes() == dst.read_bytes()


def ordered_directives(directives_dir: Path, target_env: str = "wsl") -> list[Path]:
    """Return directive markdown paths in concatenation order followed by target policy."""
    by_name = {
        p.name: p
        for p in directives_dir.glob("*.md")
        if p.is_file() and not p.name.startswith(".")
    }
    ordered = [by_name.pop(name) for name in DIRECTIVE_PRIORITY if name in by_name]
    ordered.extend(by_name[name] for name in sorted(by_name))
    target_file = directives_dir / "targets" / f"{target_env}.md"
    if not target_file.is_file():
        raise ValueError(f"Missing target directive file: {target_file}")
    ordered.append(target_file)
    return ordered


def build_gemini_md(directives_dir: Path, target_env: str = "wsl") -> str:
    """Concatenate shared directives and the target policy markdown into GEMINI.md text."""
    sections = [
        p.read_text(encoding="utf-8").strip()
        for p in ordered_directives(directives_dir, target_env=target_env)
    ]
    body = "\n\n---\n\n".join(s for s in sections if s)
    if not body:
        raise ValueError(f"No directive markdown files found in {directives_dir}")
    return body + "\n"


def iter_skill_dirs(repo_root: Path, profile: str = "all") -> list[Path]:
    """Return sorted skill directories included in the requested deployment profile."""
    if profile not in PROFILE_SCOPES:
        raise ValueError(f"Unknown skill profile '{profile}'; expected one of {PROFILE_CHOICES}")

    skill_dirs: list[Path] = []
    for scope in PROFILE_SCOPES[profile]:
        scope_dir = repo_root / "skills" / scope
        if not scope_dir.is_dir():
            continue
        for candidate in sorted(scope_dir.iterdir()):
            if (
                candidate.is_dir()
                and not candidate.name.startswith(".")
                and candidate.name != "__pycache__"
            ):
                skill_dirs.append(candidate)
    return skill_dirs


def skill_rel_files(skill_dir: Path) -> set[Path]:
    """Return relative non-ignored file paths inside a skill directory."""
    rels: set[Path] = set()
    for path in skill_dir.rglob("*"):
        rel = path.relative_to(skill_dir)
        if path.is_dir() or path.suffix in {".pyc", ".pyo"}:
            continue
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        rels.add(rel)
    return rels


def remove_entry(path: Path) -> None:
    """Delete a file, symlink, or directory tree without shutil.rmtree or symlink traversal."""
    # Unlink symlinks and Windows junctions directly instead of recursing into their targets.
    is_junction = getattr(path, "is_junction", None)
    if path.is_symlink() or (callable(is_junction) and is_junction()) or not path.is_dir():
        path.unlink()
        return
    for child in sorted(path.iterdir()):
        remove_entry(child)
    path.rmdir()


def prune_target(
    root: Path,
    skill_dirs: list[Path],
    dry_run: bool,
    prefix: str,
) -> None:
    """Remove stale config/rules files, obsolete skill folders, and deleted skill files."""
    rules_dir = root / "config" / "rules"
    if rules_dir.is_dir():
        for entry in sorted(rules_dir.iterdir()):
            if entry.name.startswith("."):
                continue
            print(f"{prefix}  [prune] {entry}")
            if not dry_run:
                remove_entry(entry)

    skills_root = root / "config" / "skills"
    if not skills_root.is_dir():
        return

    managed = {d.name for d in skill_dirs}
    for entry in sorted(skills_root.iterdir()):
        if entry.name.startswith(".") or entry.name in managed:
            continue
        print(f"{prefix}  [prune] {entry}")
        if not dry_run:
            remove_entry(entry)

    for skill_dir in skill_dirs:
        dst_dir = skills_root / skill_dir.name
        if not dst_dir.is_dir():
            continue
        for rel in sorted(skill_rel_files(dst_dir) - skill_rel_files(skill_dir)):
            stale = dst_dir / rel
            print(f"{prefix}  [prune] {stale}")
            if not dry_run:
                stale.unlink()
        if not dry_run:
            for folder in sorted(dst_dir.rglob("*"), reverse=True):
                if folder.is_dir() and not folder.is_symlink() and not any(folder.iterdir()):
                    folder.rmdir()


def _prepare_sync_sources(
    repo_root: Path,
    profile: str,
    directive_target: str,
) -> tuple[list[Path], str]:
    skill_dirs = iter_skill_dirs(repo_root, profile)
    if not skill_dirs:
        raise ValueError(f"No skill directories found in {repo_root / 'skills'} (profile={profile})")
    for skill_dir in skill_dirs:
        if not (skill_dir / "SKILL.md").is_file():
            raise ValueError(f"Missing SKILL.md in {skill_dir}")
    gemini_content = build_gemini_md(repo_root / "directives", target_env=directive_target)
    return skill_dirs, gemini_content


def _prepare_target_permissions(
    tpl_path: Path,
    config_json: Path,
    home_dir: str,
) -> str:
    if not tpl_path.is_file():
        raise ValueError(f"Missing permission template: {tpl_path}")
    tpl = load_json(tpl_path)
    cur = load_json(config_json) if config_json.is_file() else {}
    return format_config_json(merge_permission_grants(cur, tpl, home_dir=home_dir))


def sync_target(
    repo_root: Path,
    target: SyncTarget,
    dry_run: bool,
    sync_permissions: bool,
    prune: bool,
    profile: str = "all",
) -> bool:
    """Sync directives, skills, and optional permissions to one Antigravity target."""
    root = target.gemini_root
    if is_unmounted_target(target):
        print(f"[SKIP] {target.name} ({target_mount_probe(target)} not mounted)")
        return True
    if target.require_existing_home and not root.parent.is_dir():
        print(
            f"[FAIL] {target.name}: target home directory not found: {root.parent}",
            file=sys.stderr,
        )
        return False

    gemini_md = root / "GEMINI.md"
    skills_dir = root / "config" / "skills"
    tpl_path = repo_root / "configs" / target.permission_template
    config_json = root / "config" / "config.json"

    try:
        skill_dirs, gemini_content = _prepare_sync_sources(
            repo_root,
            profile,
            target.directive_target,
        )
        # Validate and merge config.json before mutating directives or pruning target directories.
        merged_permissions_text = (
            _prepare_target_permissions(tpl_path, config_json, home_dir=target_home_dir(target))
            if sync_permissions
            else None
        )
    except (OSError, ValueError) as exc:
        print(f"[FAIL] {target.name}: deployment failed: {exc}", file=sys.stderr)
        return False

    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{prefix}=== Deploying to {target.name} ({root}) [profile={profile}] ===")

    try:
        # Directives are concatenated into <gemini_root>/GEMINI.md rather than copied into config/rules/
        # so Antigravity loads a single deterministic instruction block per turn.
        if not dry_run:
            gemini_md.parent.mkdir(parents=True, exist_ok=True)
            write_lf_text(gemini_md, gemini_content)
        print(f"{prefix}  [directives] -> {gemini_md}")

        # Prune before copying so stale files or directories cannot block updated skill paths.
        if prune:
            prune_target(root, skill_dirs, dry_run, prefix)

        if not dry_run:
            for skill_dir in skill_dirs:
                dst_dir = skills_dir / skill_dir.name
                shutil.copytree(skill_dir, dst_dir, ignore=SKILL_IGNORE, dirs_exist_ok=True)
        print(f"{prefix}  [skills] -> {skills_dir} ({len(skill_dirs)} skills)")

        if merged_permissions_text is not None:
            if not dry_run:
                config_json.parent.mkdir(parents=True, exist_ok=True)
                write_lf_text(config_json, merged_permissions_text)
            print(f"{prefix}  [permissions] -> {config_json}")
    except (OSError, shutil.Error, ValueError) as exc:
        print(f"[FAIL] {target.name}: deployment failed: {exc}", file=sys.stderr)
        return False

    return True
