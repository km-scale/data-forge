#!/usr/bin/env python3
"""Check recipe folders: metadata, required files and, if published, the converted sample.

Usage
-----
    python scripts/check_recipes.py                     # all recipes
    python scripts/check_recipes.py recipes/foo ...     # selected recipes
    python scripts/check_recipes.py --no-validate ...   # skip the sample validation

Exit code 1 if any recipe fails.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "recipes"

FILES = ("recipe.yaml", "convert.py", "README.md", "pixi.toml", "pixi.lock")
REQUIRED: dict[str, type] = {
    "name": str,
    "issue": int,
    "maintainers": list,
    "license": str,
    "source": dict,
    "target": dict,
}
REQUIRED_SOURCE = ("description", "format", "grid")
REQUIRED_TARGET = ("max_zoom", "min_zoom", "variables")
HOSTING_LOCATIONS = ("producer", "waterpark", "undecided")


def load_recipe(folder: Path) -> dict[str, Any]:
    """Read ``recipe.yaml`` of a recipe folder.

    Examples
    --------
    >>> load_recipe(RECIPES / "_template")["target"]["max_zoom"]
    9
    """
    with (folder / "recipe.yaml").open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = "recipe.yaml must contain a mapping"
        raise TypeError(msg)
    return data


def check_metadata(recipe: dict[str, Any], folder_name: str) -> list[str]:
    """Return problems with the recipe metadata.

    Examples
    --------
    >>> r = load_recipe(RECIPES / "_template")
    >>> check_metadata(r, "my-dataset")
    ["'issue' must be the data-offer issue number"]
    >>> check_metadata({**r, "issue": 3, "name": "other"}, "my-dataset")
    ["name 'other' does not match folder 'my-dataset'"]
    >>> check_metadata({"name": "x"}, "x")[:2]
    ["'issue' missing or not a int", "'maintainers' missing or not a list"]
    """
    errs = [
        f"'{key}' missing or not a {typ.__name__}"
        for key, typ in REQUIRED.items()
        if not isinstance(recipe.get(key), typ)
    ]
    if errs:
        return errs

    if recipe["name"] != folder_name:
        errs.append(f"name '{recipe['name']}' does not match folder '{folder_name}'")
    if recipe["issue"] <= 0:
        errs.append("'issue' must be the data-offer issue number")
    errs += [f"source.{k} missing" for k in REQUIRED_SOURCE if not recipe["source"].get(k)]
    errs += [f"target.{k} missing" for k in REQUIRED_TARGET if recipe["target"].get(k) is None]
    try:
        zmin, zmax = int(recipe["target"]["min_zoom"]), int(recipe["target"]["max_zoom"])
    except (TypeError, ValueError, KeyError):
        errs.append("min_zoom / max_zoom must be integers")
    else:
        if not 0 <= zmin <= zmax <= 15:
            errs.append(f"zoom range {zmin}..{zmax} invalid")
    return errs


def check_folder(folder: Path, validate: bool) -> list[str]:
    """Return all problems of a recipe folder (files, metadata, sample).

    Examples
    --------
    >>> import shutil, tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     folder = Path(d) / "my-dataset"
    ...     _ = shutil.copytree(RECIPES / "_template", folder)
    ...     (folder / "pixi.lock").touch()
    ...     (folder / "README.md").unlink()
    ...     check_folder(folder, validate=False)
    ['missing README.md']
    """
    errs = [f"missing {f}" for f in FILES if not (folder / f).is_file()]
    if errs:
        return errs
    try:
        recipe = load_recipe(folder)
    except (yaml.YAMLError, TypeError) as e:
        return [f"recipe.yaml invalid: {e}"]
    errs = check_metadata(recipe, folder.name)
    errs += check_workspace_name(folder)
    errs += check_hosting(recipe)

    sample = (recipe.get("sample_output") or {}).get("url")
    if validate and sample and not errs:
        errs += validate_sample(sample, recipe["sample_output"].get("endpoint_url"))
    elif validate and not sample:
        print("  no sample_output.url yet, skipping validation")
    return errs


def check_hosting(recipe: dict[str, Any]) -> list[str]:
    """Return problems with the optional ``hosting`` section.

    Examples
    --------
    >>> check_hosting(load_recipe(RECIPES / "_template"))
    []
    >>> check_hosting({"hosting": {"full": {"location": "somewhere"}}})
    ["hosting.full.location must be one of ('producer', 'waterpark', 'undecided')"]
    >>> subset = {"url": "s3://b/x.zarr", "description": None}
    >>> check_hosting({"hosting": {"full": {"location": "producer"}, "waterpark_subset": subset}})
    ['hosting.waterpark_subset.description is required when a subset url is set']
    >>> check_hosting({})  # hosting is optional
    []
    >>> check_hosting({"hosting": "waterpark"})
    ['hosting must be a mapping with full / waterpark_subset']
    """
    hosting = recipe.get("hosting")
    if hosting is None:
        return []
    if not isinstance(hosting, dict):
        return ["hosting must be a mapping with full / waterpark_subset"]
    errs = []
    full = hosting.get("full") or {}
    if full.get("location", "undecided") not in HOSTING_LOCATIONS:
        errs.append(f"hosting.full.location must be one of {HOSTING_LOCATIONS}")
    subset = hosting.get("waterpark_subset") or {}
    if subset.get("url") and not subset.get("description"):
        errs.append("hosting.waterpark_subset.description is required when a subset url is set")
    return errs


def check_workspace_name(folder: Path) -> list[str]:
    """Check that the pixi workspace of a recipe is named like its folder.

    Examples
    --------
    >>> check_workspace_name(RECIPES / "_template")
    ["pixi.toml: workspace name 'my-dataset' does not match folder '_template'"]
    """
    try:
        with (folder / "pixi.toml").open("rb") as f:
            name = tomllib.load(f).get("workspace", {}).get("name")
    except tomllib.TOMLDecodeError as e:
        return [f"pixi.toml invalid: {e}"]
    if name != folder.name:
        return [f"pixi.toml: workspace name {name!r} does not match folder {folder.name!r}"]
    return []


def validate_sample(url: str, endpoint_url: str | None) -> list[str]:
    """Run the HEALPix validator on a published sample.

    Examples
    --------
    >>> validate_sample("/does/not/exist.zarr", None)  # doctest: +ELLIPSIS
      ERROR [/] cannot open store: ...
    ['sample output failed validation']
    """
    from validate_healpix_zarr import validate_store  # noqa: PLC0415 - heavy imports only when needed

    opts: dict[str, Any] = {}
    if url.startswith("s3://"):
        opts["anon"] = True
        if endpoint_url:
            opts["client_kwargs"] = {"endpoint_url": endpoint_url}
    rep = validate_store(url, opts or None)
    for m in rep.warnings:
        print(f"  WARN  {m}")
    for m in rep.errors:
        print(f"  ERROR {m}")
    return ["sample output failed validation"] if rep.failed(strict=False) else []


def recipe_folders(paths: list[Path], include_template: bool = False) -> list[Path]:
    """Recipe folders touched by ``paths`` (files or folders), or all recipes if empty.

    Paths outside ``recipes/`` are ignored, so a list of changed files can be passed directly.

    Examples
    --------
    >>> [p.name for p in recipe_folders([RECIPES / "_template"])]
    []
    >>> files = [
    ...     RECIPES / "_template" / "convert.py",
    ...     RECIPES / "_template" / "recipe.yaml",
    ...     ROOT / "README.md",
    ... ]
    >>> [p.name for p in recipe_folders(files, include_template=True)]
    ['_template']
    """
    if not paths:
        folders = sorted(d for d in RECIPES.iterdir() if d.is_dir())
    else:
        found: set[Path] = set()
        for p in paths:
            rel = p.resolve().relative_to(ROOT) if p.resolve().is_relative_to(ROOT) else None
            if rel is not None and len(rel.parts) >= 2 and rel.parts[0] == "recipes":
                found.add(RECIPES / rel.parts[1])
        folders = sorted(found)
    return [f for f in folders if f.is_dir() and (include_template or f.name != "_template")]


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    p.add_argument("paths", nargs="*", type=Path, help="recipe folders or files in them")
    p.add_argument("--no-validate", action="store_true")
    args = p.parse_args(argv)

    folders = recipe_folders(args.paths)
    if not folders:
        print("no recipes to check")
        return 0

    failed = 0
    for f in folders:
        print(f"{f.name}:")
        errs = check_folder(f, not args.no_validate)
        for e in errs:
            print(f"  ERROR {e}")
        print("  ok" if not errs else "  FAILED")
        failed += bool(errs)
    print(f"\n{len(folders) - failed}/{len(folders)} recipes ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
