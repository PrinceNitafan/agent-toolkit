"""Repository integrity verification and deployed target drift checks."""

from __future__ import annotations

import importlib.util
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from deploy.core.permissions import (
    PERMISSION_TEMPLATES,
    expanded_target_env,
    invalid_file_grant_rules,
    load_json,
    missing_safety_grants,
    permission_grants,
    template_target_env,
)
from deploy.core.sync import (
    build_gemini_md,
    files_match,
    iter_skill_dirs,
    norm_text,
    skill_rel_files,
)
from deploy.core.targets import SyncTarget, target_home_dir

REPO_SKIP_DIRS: frozenset[str] = frozenset({
    ".git",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
})
REPO_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_/-])"
    r"((?:directives|skills|deploy|configs|references|scripts)/[A-Za-z0-9_./*<>-]+)"
)
DEPLOYED_SKILL_PATH_RE = re.compile(r"~/.gemini/config/skills/([A-Za-z0-9_./*<>-]+)")


def load_content_scanner(repo_root: Path) -> Callable[[Path, bool], list[str]]:
    """Load check_content.scan_file without mutating sys.path or writing __pycache__."""
    script_path = repo_root / "skills" / "shared" / "humanize" / "scripts" / "check_content.py"
    if not script_path.is_file():
        raise FileNotFoundError(f"Missing content scanner script: {script_path}")

    spec = importlib.util.spec_from_file_location("agent_toolkit_check_content", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load content checker at {script_path}")

    module = importlib.util.module_from_spec(spec)
    prev_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prev_bytecode
    return cast(Callable[[Path, bool], list[str]], module.scan_file)


def parse_frontmatter(lines: list[str]) -> dict[str, str] | None:
    """Parse flat YAML frontmatter without third-party PyYAML dependencies."""
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end_idx is None:
        return None

    fields: dict[str, str] = {}
    for line in lines[1:end_idx]:
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("\"'")
    return fields


def concrete_path_candidate(raw: str) -> str | None:
    """Strip trailing prose punctuation and skip globs, placeholders, and directory prefixes."""
    if raw.endswith("..."):
        return None
    cand = raw.rstrip(".,:;")
    if not cand or any(ch in cand for ch in "*<>") or cand.endswith("/"):
        return None
    return cand


def check_markdown_paths(
    repo_root: Path,
    md_path: Path,
    skills_by_name: dict[str, Path],
) -> list[str]:
    """Validate repo-relative and deployed ~/.gemini/config/skills path references in markdown."""
    issues: list[str] = []
    rel_parts = md_path.relative_to(repo_root).parts
    in_skills = bool(rel_parts and rel_parts[0] == "skills")
    skill_root = repo_root.joinpath(*rel_parts[:3]) if in_skills and len(rel_parts) >= 3 else md_path.parent

    try:
        lines = md_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return [f"{md_path}:1: file is not valid UTF-8"]

    for line_no, line in enumerate(lines, 1):
        for match in REPO_PATH_RE.finditer(line):
            cand = concrete_path_candidate(match.group(1))
            if cand is None:
                continue
            if in_skills and cand.startswith(("directives/", "skills/")):
                issues.append(
                    f"{md_path}:{line_no}: repo-only path '{cand}' invalid in deployed skill"
                )
                continue
            # Inside a skill, references/ and scripts/ resolve relative to that skill's folder.
            is_local = in_skills and cand.startswith(("references/", "scripts/"))
            resolved = (skill_root / cand) if is_local else (repo_root / cand)
            if not resolved.exists():
                issues.append(f"{md_path}:{line_no}: broken repo path '{cand}'")

        for match in DEPLOYED_SKILL_PATH_RE.finditer(line):
            cand = concrete_path_candidate(match.group(1))
            if cand is None:
                continue
            skill_name, *rest = cand.split("/", 1)
            target_dir = skills_by_name.get(skill_name)
            if target_dir is None or (rest and not (target_dir / rest[0]).exists()):
                issues.append(
                    f"{md_path}:{line_no}: broken deployed skill path "
                    f"'~/.gemini/config/skills/{cand}'"
                )

    return issues


def check_skill_frontmatter(skill_dirs: list[Path]) -> list[str]:
    """Validate SKILL.md presence, UTF-8 decoding, and required name/description frontmatter."""
    issues: list[str] = []
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            issues.append(f"{skill_dir}: missing SKILL.md")
            continue
        try:
            lines = skill_md.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            issues.append(f"{skill_md}:1: file is not valid UTF-8")
            continue
        fields = parse_frontmatter(lines)
        if fields is None:
            issues.append(f"{skill_md}:1: missing valid YAML frontmatter delimiters '---'")
            continue
        if fields.get("name") != skill_dir.name:
            issues.append(
                f"{skill_md}:1: frontmatter name '{fields.get('name')}' != '{skill_dir.name}'"
            )
        if not fields.get("description"):
            issues.append(f"{skill_md}:1: frontmatter missing non-empty 'description'")
    return issues


def check_target_assets(repo_root: Path) -> list[str]:
    """Validate directive builds and permission JSON templates for every target environment."""
    issues: list[str] = []
    for target_env, tpl_name in PERMISSION_TEMPLATES.items():
        try:
            build_gemini_md(repo_root / "directives", target_env=target_env)
        except (OSError, ValueError) as exc:
            issues.append(f"{repo_root / 'directives'}: {exc}")

        tpl_path = repo_root / "configs" / tpl_name
        if not tpl_path.is_file():
            issues.append(f"Missing permission template: {tpl_path}")
            continue
        try:
            grants = permission_grants(load_json(tpl_path))
        except (OSError, ValueError) as exc:
            issues.append(f"{tpl_path}: {exc}")
            continue
        if not grants:
            issues.append(f"{tpl_path}: missing userSettings.globalPermissionGrants")
            continue
        for bucket, rule, reason in invalid_file_grant_rules(
            grants,
            target_env=target_env,
            allow_home_placeholder=True,
        ):
            issues.append(f"{tpl_path}: invalid {bucket} rule '{rule}': {reason}")
    return issues


def check_repo(repo_root: Path, fix: bool = False) -> list[str]:
    """Verify repository frontmatter, directives, permission templates, content hygiene, and links."""
    skill_dirs = iter_skill_dirs(repo_root)
    skills_by_name = {d.name: d for d in skill_dirs}
    issues = (
        [f"No skill directories found in {repo_root / 'skills'}"]
        if not skill_dirs
        else check_skill_frontmatter(skill_dirs)
    )
    issues.extend(check_target_assets(repo_root))

    try:
        scan_file = load_content_scanner(repo_root)
    except (OSError, RuntimeError) as exc:
        issues.append(f"{repo_root}: {exc}")
        scan_file = None

    for md_path in sorted(repo_root.rglob("*.md")):
        rel_parts = md_path.relative_to(repo_root).parts
        if any(part in REPO_SKIP_DIRS for part in rel_parts[:-1]):
            continue
        if not md_path.is_file():
            issues.append(f"{md_path}: broken symlink or unreadable markdown file")
            continue
        if scan_file is not None:
            issues.extend(scan_file(md_path, fix))
        issues.extend(check_markdown_paths(repo_root, md_path, skills_by_name))

    return issues


def _check_gemini_drift(repo_root: Path, target: SyncTarget) -> list[str]:
    gemini_md = target.gemini_root / "GEMINI.md"
    try:
        expected_md = norm_text(
            build_gemini_md(repo_root / "directives", target_env=target.directive_target)
        )
    except (OSError, ValueError) as exc:
        return [f"[{target.name}] Unable to build expected GEMINI.md: {exc}"]

    if not gemini_md.is_file():
        return [f"[{target.name}] GEMINI.md drift or missing: {gemini_md}"]
    try:
        actual_md = norm_text(gemini_md.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError) as exc:
        return [f"[{target.name}] Unable to read GEMINI.md ({gemini_md}): {exc}"]
    if actual_md != expected_md:
        return [f"[{target.name}] GEMINI.md drift or missing: {gemini_md}"]
    return []


def _check_rules_drift(target: SyncTarget) -> list[str]:
    rules_dir = target.gemini_root / "config" / "rules"
    if not rules_dir.is_dir():
        return []
    return [
        f"[{target.name}] Stale file in config/rules (run --prune): {item}"
        for item in sorted(rules_dir.rglob("*"))
        if not item.name.startswith(".") and (item.is_symlink() or not item.is_dir())
    ]


def _check_skills_drift(repo_root: Path, target: SyncTarget, profile: str) -> list[str]:
    drift: list[str] = []
    skills_root = target.gemini_root / "config" / "skills"
    skill_dirs = iter_skill_dirs(repo_root, profile)
    if not skill_dirs:
        return [f"[{target.name}] No skill directories found in {repo_root / 'skills'} (profile={profile})"]

    managed = {d.name for d in skill_dirs}
    if skills_root.is_dir():
        for entry in sorted(skills_root.iterdir()):
            if not entry.name.startswith(".") and entry.name not in managed:
                drift.append(
                    f"[{target.name}] Unexpected entry in config/skills (run --prune): {entry}"
                )

    for skill_dir in skill_dirs:
        dst_dir = skills_root / skill_dir.name
        expected_rels = skill_rel_files(skill_dir)
        for rel in sorted(expected_rels):
            dst = dst_dir / rel
            if not dst.is_file() or not files_match(skill_dir / rel, dst):
                drift.append(f"[{target.name}] Skill drift: {dst}")
        if dst_dir.is_dir():
            for rel in sorted(skill_rel_files(dst_dir) - expected_rels):
                drift.append(f"[{target.name}] Stale skill file (run --prune): {dst_dir / rel}")

    return drift


def _check_permissions_drift(repo_root: Path, target: SyncTarget) -> list[str]:
    tpl_path = repo_root / "configs" / target.permission_template
    config_json = target.gemini_root / "config" / "config.json"
    if not tpl_path.is_file():
        return [f"[{target.name}] Missing permission template: {tpl_path}"]
    if not config_json.is_file():
        return [f"[{target.name}] Missing config.json: {config_json}"]

    home_dir = target_home_dir(target)
    tpl_env = template_target_env(target.permission_template)
    try:
        tpl_cfg = load_json(tpl_path)
        dep_cfg = load_json(config_json)
        tpl_grants = permission_grants(tpl_cfg)
        dep_grants = permission_grants(dep_cfg)
        missing = missing_safety_grants(tpl_cfg, dep_cfg, home_dir=home_dir)
    except (OSError, ValueError) as exc:
        return [f"[{target.name}] {exc}"]

    drift = [
        f"[{target.name}] Invalid template {bucket} rule '{rule}': {reason}"
        for bucket, rule, reason in invalid_file_grant_rules(
            tpl_grants,
            target_env=tpl_env,
            allow_home_placeholder=True,
        )
    ]
    drift.extend(
        f"[{target.name}] Invalid config.json {bucket} rule '{rule}': {reason}"
        for bucket, rule, reason in invalid_file_grant_rules(
            dep_grants,
            target_env=expanded_target_env(tpl_env, home_dir),
            allow_home_placeholder=False,
        )
    )
    drift.extend(f"[{target.name}] Missing {bucket} rule '{rule}'" for bucket, rule in missing)
    return drift


def check_drift(
    repo_root: Path,
    target: SyncTarget,
    check_permissions: bool,
    profile: str = "all",
) -> list[str]:
    """Compare deployed GEMINI.md, rules, skills, and optional permissions against the repo."""
    if target.require_existing_home and not target.gemini_root.parent.is_dir():
        return [f"[{target.name}] Target home directory not found: {target.gemini_root.parent}"]
    if not target.gemini_root.exists():
        return [f"[{target.name}] Target root not deployed: {target.gemini_root}"]

    drift = _check_gemini_drift(repo_root, target)
    drift.extend(_check_rules_drift(target))
    drift.extend(_check_skills_drift(repo_root, target, profile))
    if check_permissions:
        drift.extend(_check_permissions_drift(repo_root, target))
    return drift
