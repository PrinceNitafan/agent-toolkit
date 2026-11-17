#!/usr/bin/env python3
"""Scan markdown, source code, and configuration files for Unicode dashes, smart quotes, and AI buzzwords."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PUNCT_MAP = str.maketrans({
    "\u2014": "-", "\u2013": "-", "\u2015": "-", "\u2012": "-", "\u2212": "-",
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'",
    "\u201a": "'", "\u201b": "'",
})
PUNCT_RE = re.compile("[" + "".join(re.escape(chr(cp)) for cp in PUNCT_MAP) + "]")
INLINE_CODE_RE = re.compile(r"``.+?``|`[^`]*`")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
BUZZWORD_RE = re.compile(
    r"\b(delve|delving|tapestry|testament|landscape|pivotal|beacon|foster|streamline|"
    r"dive deep|diving deep|seamless|multifaceted|holistic|crucial|furthermore|moreover|"
    r"it is important to note|it's important to note|it is worth noting|it's worth noting)\b",
    re.IGNORECASE,
)
SKIP_DIRS = {".git", "build", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv", "venv", "node_modules"}
TEXT_EXTS = {
    ".md", ".txt", ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".sql",
    ".cpp", ".hpp", ".cc", ".cxx", ".h", ".hxx", ".cmake",
    ".yml", ".yaml", ".json", ".sh", ".toml", ".css", ".html",
}


def iter_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(
        p for p in target.rglob("*")
        if p.is_file()
        and not any(part in SKIP_DIRS for part in p.relative_to(target).parts[:-1])
        and (p.suffix.lower() in TEXT_EXTS or p.name == "CMakeLists.txt")
    )


def next_fence_state(line: str, fence: tuple[str, int] | None) -> tuple[str, int] | None:
    """Track CommonMark-style fenced code block state across backtick and tilde fences."""
    match = FENCE_RE.match(line)
    if not match:
        return fence
    marker, rest = match.groups()
    if fence is None:
        return (marker[0], len(marker)) if (marker[0] == "~" or "`" not in rest) else None
    if marker[0] == fence[0] and len(marker) >= fence[1] and not rest.strip():
        return None
    return fence


def scan_file(path: Path, fix: bool) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return []
    if fix:
        fixed = text.translate(PUNCT_MAP)
        if fixed != text:
            try:
                with path.open("w", encoding="utf-8", newline="\n") as handle:
                    handle.write(fixed)
            except OSError as exc:
                return [f"{path}: unable to write --fix changes: {exc}"]
            text = fixed
            print(f"[FIXED] {path}")

    issues: list[str] = []
    fence: tuple[str, int] | None = None
    for line_no, line in enumerate(text.splitlines(), 1):
        if path.suffix.lower() == ".md":
            fence = next_fence_state(line, fence)
        if PUNCT_RE.search(line):
            issues.append(f"{path}:{line_no}: forbidden Unicode dash or smart quote")
        if fence is None and path.name != "check_content.py":
            prose = INLINE_CODE_RE.sub("", line) if path.suffix.lower() == ".md" else line
            for match in BUZZWORD_RE.finditer(prose):
                issues.append(f"{path}:{line_no}: banned AI phrase '{match.group(0)}'")
    return issues


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="File or directory to scan.")
    p.add_argument("--fix", action="store_true", help="Auto-replace Unicode dashes and smart quotes with ASCII.")
    args = p.parse_args(argv)
    if not args.path.exists():
        print(f"Error: path not found: {args.path}", file=sys.stderr)
        return 1
    issues = [item for f in iter_files(args.path) for item in scan_file(f, args.fix)]
    for item in issues:
        print(f"[FAIL] {item}")
    print("OK: content check passed." if not issues else f"Failed with {len(issues)} issue(s).")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
