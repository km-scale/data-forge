#!/usr/bin/env python3
"""Start a new recipe from ``recipes/_template``.

Usage
-----
    pixi run new-recipe <name>

Copies the template (without its local ``.pixi`` environment) and sets the
name in ``recipe.yaml`` and ``pixi.toml``.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

RECIPES = Path(__file__).resolve().parent.parent / "recipes"
TEMPLATE = "_template"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
PLACEHOLDER = "my-dataset"


def create(name: str, recipes: Path = RECIPES) -> Path:
    """Copy the template to ``recipes/<name>`` and fill in the name.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     _ = shutil.copytree(RECIPES / TEMPLATE, Path(d) / TEMPLATE)
    ...     new = create("icon-dpp0066", Path(d))
    ...     (
    ...         "name: icon-dpp0066" in (new / "recipe.yaml").read_text(),
    ...         'name = "icon-dpp0066"' in (new / "pixi.toml").read_text(),
    ...         (new / ".pixi").exists(),
    ...     )
    (True, True, False)
    >>> create("Bad Name!")
    Traceback (most recent call last):
    ValueError: invalid recipe name 'Bad Name!': use lowercase letters, digits, '.', '_' or '-'
    """
    if not NAME_RE.match(name):
        msg = f"invalid recipe name {name!r}: use lowercase letters, digits, '.', '_' or '-'"
        raise ValueError(msg)
    target = recipes / name
    if target.exists():
        msg = f"{target} already exists"
        raise FileExistsError(msg)
    shutil.copytree(recipes / TEMPLATE, target, ignore=shutil.ignore_patterns(".pixi", "__pycache__"))
    for fname, old, new in (
        ("recipe.yaml", f"name: {PLACEHOLDER}", f"name: {name}"),
        ("pixi.toml", f'name = "{PLACEHOLDER}"', f'name = "{name}"'),
    ):
        path = target / fname
        path.write_text(path.read_text().replace(old, new, 1))
    return target


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: new_recipe.py <name>")
        return 2
    try:
        target = create(args[0])
    except (ValueError, FileExistsError) as e:
        print(f"error: {e}")
        return 1
    rel = target.relative_to(RECIPES.parent)
    print(f"created {rel}")
    print("next: set 'issue' in recipe.yaml, adapt convert.py, then run `pixi install` in that folder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
