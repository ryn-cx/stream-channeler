# TODO: Validate
"""Add `# TODO: Validate` markers to every file, function, and class.

Usage: python scripts/add_validate_markers.py app tests plugins
"""

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

type Definition = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef

MARKER = "# TODO: Validate"
EXEMPT_PARTS = {"versions", "__pycache__", ".venv", "node_modules", ".git"}


# TODO: Validate
def definition_start_line(node: Definition) -> int:
    lines = [node.lineno]
    lines.extend(decorator.lineno for decorator in node.decorator_list)
    return min(lines)


# TODO: Validate
def collect_insert_lines(tree: ast.Module) -> set[int]:
    insert_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            insert_lines.add(definition_start_line(node) - 1)
    return insert_lines


# TODO: Validate
def process_file(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines(keepends=True)

    insert_indexes = collect_insert_lines(tree)
    insert_indexes.add(0)

    changed = False
    for index in sorted(insert_indexes, reverse=True):
        neighbor_index = index if index == 0 else index - 1
        already_marked = (
            neighbor_index < len(lines)
            and lines[neighbor_index].strip() == MARKER
        )
        if already_marked:
            continue
        target = lines[index] if index < len(lines) else ""
        indent = target[: len(target) - len(target.lstrip())]
        newline = "\r\n" if target.endswith("\r\n") else "\n"
        lines.insert(index, f"{indent}{MARKER}{newline}")
        changed = True

    if changed:
        path.write_text("".join(lines), encoding="utf-8", newline="")
    return changed


# TODO: Validate
def iter_python_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if EXEMPT_PARTS.isdisjoint(path.parts):
            yield path


# TODO: Validate
def main() -> None:
    roots = [Path(argument) for argument in sys.argv[1:]] or [Path("app")]
    changed_count = 0
    total_count = 0
    for root in roots:
        for path in iter_python_files(root):
            total_count += 1
            if process_file(path):
                changed_count += 1
                print(f"updated {path}")
    print(f"{changed_count} of {total_count} files updated")


if __name__ == "__main__":
    main()
