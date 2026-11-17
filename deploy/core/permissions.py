"""Permission template loading, merging, and safety guardrail verification."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

PERMISSION_TEMPLATES: dict[str, str] = {
    "wsl": "antigravity-wsl-template.json",
    "windows": "antigravity-windows-template.json",
}
TEMPLATE_ENVIRONMENTS: dict[str, str] = {
    tpl_name: target_env for target_env, tpl_name in PERMISSION_TEMPLATES.items()
}
PERMISSION_BUCKETS: tuple[str, ...] = ("allow", "ask", "deny")
SAFETY_BUCKETS: tuple[str, ...] = ("ask", "deny")
FILE_RULE_PREFIXES: tuple[str, ...] = ("read_file(", "write_file(")
HOME_PREFIXES_BY_ENV: dict[str | None, tuple[str, ...]] = {
    "wsl": ("{home}/",),
    "windows": ("{home}\\", "{home}/"),
    None: ("{home}/", "{home}\\"),
}


def template_target_env(template_name: str) -> str | None:
    """Return the target environment ('wsl' or 'windows') for a known template filename."""
    return TEMPLATE_ENVIRONMENTS.get(template_name)


def expanded_target_env(target_env: str | None, home_dir: str) -> str | None:
    """Relax Windows path checks only when a Linux test override supplies a POSIX home_dir."""
    return None if (target_env == "windows" and home_dir.startswith("/")) else target_env


def _is_posix_abs(path: str) -> bool:
    """Return True for single-slash POSIX paths; reject '//' glob prefixes like '//**/.env'."""
    return path.startswith("/") and not path.startswith("//")


def _is_windows_abs(path: str) -> bool:
    """Return True for Windows drive-letter or UNC absolute paths."""
    is_drive = (
        len(path) >= 3
        and path[0].isascii()
        and path[0].isalpha()
        and path[1] == ":"
        and path[2] in ("\\", "/")
    )
    is_unc = len(path) >= 5 and path.startswith("\\\\") and path[2] not in ("\\", "/")
    return is_drive or is_unc


def file_grant_path_error(
    rule: str,
    *,
    target_env: str | None = None,
    allow_home_placeholder: bool = False,
) -> str | None:
    """Return an error reason when a read_file/write_file rule uses a non-absolute or malformed path."""
    if not rule.startswith(FILE_RULE_PREFIXES):
        return None
    if not rule.endswith(")"):
        return "malformed file rule (missing closing ')')"

    path = rule[rule.index("(") + 1 : -1]
    if not path or path != path.strip() or "\0" in path:
        return "empty or whitespace-padded file path"
    if ".." in (seg for seg in path.replace("\\", "/").split("/") if seg):
        return "path traversal '..' is not allowed in permission rules"

    if "{home}" in path:
        if not allow_home_placeholder:
            return "unexpanded '{home}' placeholder in permission rule"
        prefixes = HOME_PREFIXES_BY_ENV.get(target_env, HOME_PREFIXES_BY_ENV[None])
        valid_home = path == "{home}" or path.startswith(prefixes)
        return None if valid_home else "invalid '{home}' placeholder path"

    if target_env == "wsl":
        is_abs = _is_posix_abs(path)
    elif target_env == "windows":
        is_abs = _is_windows_abs(path)
    else:
        is_abs = _is_posix_abs(path) or _is_windows_abs(path)

    if not is_abs:
        return (
            f"non-absolute file path '{path}' "
            "(globalPermissionGrants requires absolute paths)"
        )
    return None


def invalid_file_grant_rules(
    grants: dict[str, list[str]],
    *,
    target_env: str | None = None,
    allow_home_placeholder: bool = False,
) -> list[tuple[str, str, str]]:
    """Return (bucket, rule, reason) for read_file/write_file rules failing absolute-path checks."""
    invalid: list[tuple[str, str, str]] = []
    for bucket, rules in grants.items():
        for rule in rules:
            reason = file_grant_path_error(
                rule,
                target_env=target_env,
                allow_home_placeholder=allow_home_placeholder,
            )
            if reason is not None:
                invalid.append((bucket, rule, reason))
    return invalid


def validate_permission_grants(
    grants: dict[str, list[str]],
    *,
    source: Path | str = "<permissions>",
    target_env: str | None = None,
    allow_home_placeholder: bool = False,
) -> None:
    """Raise ValueError when any read_file/write_file rule in grants lacks an absolute path."""
    invalid = invalid_file_grant_rules(
        grants,
        target_env=target_env,
        allow_home_placeholder=allow_home_placeholder,
    )
    if invalid:
        details = "; ".join(f"{bucket} '{rule}': {reason}" for bucket, rule, reason in invalid)
        raise ValueError(f"Invalid file permission rule(s) in {source}: {details}")


def parse_json_object(raw_text: str, source: Path | str = "<json>") -> dict[str, Any]:
    """Parse JSON text and enforce that the root value is a JSON object."""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {source}, got {type(data).__name__}")
    return cast(dict[str, Any], data)


def load_json(path: Path) -> dict[str, Any]:
    """Load and validate a UTF-8 JSON object file from disk."""
    return parse_json_object(path.read_text(encoding="utf-8-sig"), source=path)


def format_config_json(config: dict[str, Any]) -> str:
    """Serialize an Antigravity config dictionary with stable 2-space formatting and LF newline."""
    return json.dumps(config, indent=2) + "\n"


def permission_grants(
    config: dict[str, Any],
    home_dir: str | None = None,
) -> dict[str, list[str]]:
    """Return globalPermissionGrants, expanding {home} placeholders when home_dir is given."""
    user_settings = config.get("userSettings")
    if not isinstance(user_settings, dict):
        return {}
    grants = user_settings.get("globalPermissionGrants")
    if not isinstance(grants, dict):
        return {}

    resolved: dict[str, list[str]] = {}
    for bucket, raw_rules in grants.items():
        if not isinstance(bucket, str):
            raise ValueError(
                f"Expected string bucket name in globalPermissionGrants, got {type(bucket).__name__}"
            )
        if not isinstance(raw_rules, list):
            raise ValueError(
                f"Expected list for permission bucket '{bucket}', got {type(raw_rules).__name__}"
            )
        if not all(isinstance(rule, str) for rule in raw_rules):
            raise ValueError(f"Expected string entries in permission bucket '{bucket}'")
        rules = cast(list[str], raw_rules)
        # Keep templates username-agnostic on disk while writing concrete host paths.
        resolved[bucket] = [
            rule.replace("{home}", home_dir) if home_dir is not None else rule
            for rule in rules
        ]
    return resolved


def _existing_bucket_rules(grants: dict[str, Any], bucket: str) -> list[str]:
    """Return validated string rules for one bucket in an existing config.json."""
    raw_rules = grants.get(bucket)
    if raw_rules is None:
        return []
    if not isinstance(raw_rules, list):
        raise ValueError(
            f"Expected list for existing permission bucket '{bucket}', got {type(raw_rules).__name__}"
        )
    if not all(isinstance(rule, str) for rule in raw_rules):
        raise ValueError(f"Expected string entries in existing permission bucket '{bucket}'")
    return list(cast(list[str], raw_rules))


def merge_permission_grants(
    existing: dict[str, Any],
    template: dict[str, Any],
    home_dir: str | None = None,
    target_env: str | None = None,
) -> dict[str, Any]:
    """Append missing template rules into existing config.json without erasing user-added rules."""
    raw_tpl_grants = permission_grants(template)
    validate_permission_grants(
        raw_tpl_grants,
        source="permission template",
        target_env=target_env,
        allow_home_placeholder=True,
    )
    tpl_grants = permission_grants(template, home_dir=home_dir)
    if home_dir is not None:
        validate_permission_grants(
            tpl_grants,
            source="expanded permission template",
            target_env=expanded_target_env(target_env, home_dir),
            allow_home_placeholder=False,
        )

    merged = copy.deepcopy(existing)
    user_settings = merged.get("userSettings")
    if not isinstance(user_settings, dict):
        user_settings = {}
        merged["userSettings"] = user_settings

    grants = user_settings.get("globalPermissionGrants")
    if not isinstance(grants, dict):
        grants = {}
        user_settings["globalPermissionGrants"] = grants

    for bucket in PERMISSION_BUCKETS:
        current_rules = _existing_bucket_rules(grants, bucket)
        missing_rules = [rule for rule in tpl_grants.get(bucket, []) if rule not in current_rules]
        grants[bucket] = current_rules + missing_rules
    return merged


def missing_safety_grants(
    template: dict[str, Any],
    deployed: dict[str, Any],
    home_dir: str | None = None,
) -> list[tuple[str, str]]:
    """Return missing (bucket, rule) safety guardrails from ask and deny buckets."""
    tpl_grants = permission_grants(template, home_dir=home_dir)
    dep_grants = permission_grants(deployed)
    missing: list[tuple[str, str]] = []
    # Verify only 'ask' and 'deny' safety guardrails; 'allow' may vary per workstation.
    for bucket in SAFETY_BUCKETS:
        deployed_set = set(dep_grants.get(bucket, []))
        for rule in tpl_grants.get(bucket, []):
            if rule not in deployed_set:
                missing.append((bucket, rule))
    return missing
