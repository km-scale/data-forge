#!/usr/bin/env python3
"""Run checks of each recipe inside that recipe's own pixi environment.

Recipes have their own dependencies (e.g. remapping libraries), so their strict
type check and doctests must run in their own environment, not the repo's.

Usage
-----
    python scripts/recipe_tasks.py                         # all recipes, incl. the template
    python scripts/recipe_tasks.py recipes/foo/convert.py  # only recipes touched by these paths
    python scripts/recipe_tasks.py --locked --task typecheck
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from check_recipes import recipe_folders

DEFAULT_TASKS = ("typecheck", "doctest")


def commands(folders: list[Path], tasks: tuple[str, ...], locked: bool = False) -> list[list[str]]:
    """Build the pixi commands to run, one per recipe and task.

    Examples
    --------
    >>> for cmd in commands([Path("recipes/a")], ("typecheck", "doctest"), locked=True):
    ...     print(" ".join(cmd))
    pixi run --manifest-path recipes/a/pixi.toml --locked typecheck
    pixi run --manifest-path recipes/a/pixi.toml --locked doctest
    """
    flags = ["--locked"] if locked else []
    return [
        ["pixi", "run", "--manifest-path", str(folder / "pixi.toml"), *flags, task]
        for folder in folders
        for task in tasks
    ]


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    p.add_argument("paths", nargs="*", type=Path, help="recipe folders or files in them")
    p.add_argument("--task", action="append", dest="tasks", help=f"task to run (default: {DEFAULT_TASKS})")
    p.add_argument("--locked", action="store_true", help="fail if a recipe's pixi.lock is out of date")
    args = p.parse_args(argv)

    folders = recipe_folders(args.paths, include_template=True)
    if not folders:
        print("no recipes to check")
        return 0
    failed = []
    for cmd in commands(folders, tuple(args.tasks or DEFAULT_TASKS), args.locked):
        print(f"$ {' '.join(cmd)}", flush=True)
        if subprocess.run(cmd, check=False).returncode != 0:
            failed.append(" ".join(cmd))
    if failed:
        print("\nfailed:\n  " + "\n  ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
