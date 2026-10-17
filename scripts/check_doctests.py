#!/usr/bin/env python3
"""Require a doctest example in every public function and method.

Running doctests (``pytest --doctest-modules``) only checks the examples that exist.
This script makes sure they exist: every public function, method and class in the
given files needs a docstring containing at least one ``>>>`` line.

Exempt are names starting with ``_`` and functions called ``main`` (CLI entry points).

Usage
-----
    python scripts/check_doctests.py scripts recipes
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

EXEMPT = frozenset({"main"})


def missing_doctests(source: str) -> list[tuple[int, str]]:
    r"""Return ``(line, qualified name)`` of public definitions without a doctest.

    Examples
    --------
    >>> code = '''
    ... def documented():
    ...     \"\"\"Example: >>> documented()\"\"\"
    ... def undocumented():
    ...     \"\"\"No example.\"\"\"
    ... def _private():
    ...     pass
    ... class Thing:
    ...     \"\"\"Example: >>> Thing()\"\"\"
    ...     def method(self):
    ...         pass
    ... '''
    >>> missing_doctests(code)
    [(4, 'undocumented'), (10, 'Thing.method')]
    """
    tree = ast.parse(source)
    return sorted(_walk(tree.body, prefix=""))


def _walk(nodes: list[ast.stmt], prefix: str) -> Iterator[tuple[int, str]]:
    for node in nodes:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        name = f"{prefix}{node.name}"
        public = not node.name.startswith("_") and node.name not in EXEMPT
        doc = ast.get_docstring(node) or ""
        if public and ">>>" not in doc:
            yield node.lineno, name
        if isinstance(node, ast.ClassDef):
            yield from _walk(node.body, prefix=f"{name}.")


def python_files(paths: list[Path]) -> list[Path]:
    """Expand directories into the Python files they contain, sorted.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     root = Path(d)
    ...     (root / "a.py").touch()
    ...     (root / "sub").mkdir()
    ...     (root / "sub" / "b.py").touch()
    ...     (root / "notes.txt").touch()
    ...     [p.relative_to(root).as_posix() for p in python_files([root])]
    ['a.py', 'sub/b.py']
    """
    files: list[Path] = []
    for p in paths:
        files.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])
    return files


def main(argv: list[str] | None = None) -> int:
    """Check the given files or directories and report missing doctests."""
    args = argv if argv is not None else sys.argv[1:]
    failures = 0
    for path in python_files([Path(a) for a in args or ["."]]):
        for line, name in missing_doctests(path.read_text()):
            print(f"{path}:{line}: '{name}' has no doctest example")
            failures += 1
    if failures:
        print(f"\n{failures} public definition(s) without doctest")
        return 1
    print("all public definitions have doctests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
