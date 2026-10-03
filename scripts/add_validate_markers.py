# TODO: Validate
"""Add `TODO: Validate` markers to non-Python, non-TypeScript files.

Usage: python scripts/add_validate_markers.py .
"""

import re
import sys
from collections.abc import Iterator
from pathlib import Path

HASH_EXTENSIONS = {
    ".sh",
    ".ps1",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".conf",
    ".env",
    ".jinja",
    ".dockerignore",
    ".gitignore",
    ".gitattributes",
}
HTML_EXTENSIONS = {".html", ".htm", ".md", ".mjml", ".svg", ".xml"}
CSS_EXTENSIONS = {".css", ".scss"}
MAKO_EXTENSIONS = {".mako"}
HASH_NAMES = {".env", ".gitignore", ".gitattributes", ".dockerignore", ".editorconfig"}
EXEMPT_PARTS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    "blob-report",
    "playwright-report",
    "test-results",
    "versions",
    "output",
    ".copier",
    ".auth",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
}
SHELL_DEFINITION = re.compile(
    r"^\s*(?:function\s+[A-Za-z_][A-Za-z0-9_-]*\s*(?:\(\s*\))?\s*\{"
    r"|[A-Za-z_][A-Za-z0-9_-]*\s*\(\s*\)\s*\{)"
)
POWERSHELL_DEFINITION = re.compile(
    r"^\s*(?:function|filter|class|enum)\s+[A-Za-z_][A-Za-z0-9_-]*"
)


# TODO: Validate
def comment_for(path: Path) -> tuple[str, str] | None:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if name in HASH_NAMES or name.startswith(".env") or name.startswith("dockerfile"):
        return ("# TODO: Validate", "")
    if suffix in HASH_EXTENSIONS:
        return ("# TODO: Validate", "")
    if suffix in HTML_EXTENSIONS:
        return ("<!-- TODO: Validate", " -->")
    if suffix in CSS_EXTENSIONS:
        return ("/* TODO: Validate", " */")
    if suffix in MAKO_EXTENSIONS:
        return ("## TODO: Validate", "")
    return None


# TODO: Validate
def file_marker_index(lines: list[str], suffix: str) -> int:
    if not lines:
        return 0
    first = lines[0].lstrip().lower()
    if first.startswith("#!"):
        return 1
    if suffix in {".html", ".htm", ".svg", ".xml"} and (
        first.startswith("<?xml") or first.startswith("<!doctype")
    ):
        return 1
    return 0


# TODO: Validate
def definition_indexes(path: Path, lines: list[str]) -> set[int]:
    suffix = path.suffix.lower()
    if suffix == ".sh":
        pattern = SHELL_DEFINITION
    elif suffix == ".ps1":
        pattern = POWERSHELL_DEFINITION
    else:
        return set()
    return {index for index, line in enumerate(lines) if pattern.match(line)}


# TODO: Validate
def process_file(path: Path) -> bool:
    comment = comment_for(path)
    if comment is None:
        return False
    prefix, suffix_text = comment
    marker = f"{prefix}{suffix_text}"

    source = path.read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)

    insert_indexes = definition_indexes(path, lines)
    insert_indexes.add(file_marker_index(lines, path.suffix.lower()))

    changed = False
    for index in sorted(insert_indexes, reverse=True):
        at_index = index < len(lines) and lines[index].strip() == marker
        above_index = index > 0 and lines[index - 1].strip() == marker
        if at_index or above_index:
            continue
        target = lines[index] if index < len(lines) else ""
        newline = "\r\n" if target.endswith("\r\n") else "\n"
        stripped = target.rstrip("\r\n")
        indent = stripped[: len(stripped) - len(stripped.lstrip())]
        lines.insert(index, f"{indent}{marker}{newline}")
        changed = True

    if changed:
        path.write_text("".join(lines), encoding="utf-8", newline="")
    return changed


# TODO: Validate
def iter_files(root: Path) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if not EXEMPT_PARTS.isdisjoint(path.parts):
            continue
        if comment_for(path) is not None:
            yield path


# TODO: Validate
def main() -> None:
    roots = [Path(argument) for argument in sys.argv[1:]] or [Path()]
    changed_count = 0
    total_count = 0
    for root in roots:
        for path in iter_files(root):
            total_count += 1
            if process_file(path):
                changed_count += 1
                print(f"updated {path}")
    print(f"{changed_count} of {total_count} files updated")


if __name__ == "__main__":
    main()
