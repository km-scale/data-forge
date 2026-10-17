"""Generate the recipe and tool pages of the documentation site.

Run by the ``gen-files`` plugin during ``mkdocs build``; nothing is written to disk.
For each folder in ``recipes/`` it creates a page with the recipe metadata, the
recipe README, a summary of the functions in ``convert.py`` and the full source
files in tabs. It also creates the recipe overview table and one reference page
per tool in ``scripts/``.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "recipes"
REPO = "https://github.com/km-scale/data-forge"
TEMPLATE = "_template"
TOOLS = ("validate_healpix_zarr", "check_recipes", "check_doctests")
SOURCE_TABS = (("convert.py", "python"), ("recipe.yaml", "yaml"), ("pixi.toml", "toml"))


def slug(folder: Path) -> str:
    """Page name of a recipe folder.

    Examples
    --------
    >>> slug(Path("recipes/_template")), slug(Path("recipes/icon-dpp0066"))
    ('template', 'icon-dpp0066')
    """
    return "template" if folder.name == TEMPLATE else folder.name


def function_summary(source: str) -> list[tuple[str, str]]:
    r"""Public top-level functions with the first line of their docstring.

    Examples
    --------
    >>> function_summary('''
    ... def to_healpix(ds):
    ...     \"\"\"Regrid to HEALPix.\"\"\"
    ... def _helper():
    ...     pass
    ... def main():
    ...     pass
    ... ''')
    [('to_healpix', 'Regrid to HEALPix.'), ('main', '')]
    """
    out = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            doc = ast.get_docstring(node) or ""
            out.append((node.name, doc.strip().split("\n")[0]))
    return out


def readme_body(text: str) -> str:
    r"""Drop the README's own title and shift headings down one level.

    Examples
    --------
    >>> readme_body("# Title\n\nIntro\n\n## Input\n\n- x\n")
    'Intro\n\n### Input\n\n- x'
    """
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    body = "\n".join(lines).strip()
    return re.sub(r"^(#{1,5}) ", r"#\1 ", body, flags=re.MULTILINE)


def code_block(text: str, lang: str, indent: str = "") -> str:
    """Fenced code block that survives backticks in the content.

    Examples
    --------
    >>> print(code_block("x = 1", "python"))
    ```python linenums="1"
    x = 1
    ```
    >>> code_block("```inner```", "text").startswith("````")
    True
    """
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    block = f'{fence}{lang} linenums="1"\n{text.rstrip()}\n{fence}'
    return "\n".join(indent + line if line else line for line in block.splitlines())


def _cell(value: object) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, list):
        return ", ".join(f"`{v}`" for v in value)
    if isinstance(value, dict):
        return ", ".join(f"{k}: `{v}`" for k, v in value.items())
    return str(value).replace("|", "\\|")


def period_text(recipe: dict[str, Any]) -> str:
    """Covered time period, or ``-`` if not filled in.

    Examples
    --------
    >>> period_text({"period": {"start": "2020-01-01", "end": "2029-12-31"}})
    '2020-01-01 to 2029-12-31'
    >>> period_text({})
    '-'
    """
    period: dict[str, Any] = recipe.get("period") or {}
    start, end = period.get("start"), period.get("end")
    return f"{start} to {end}" if start and end else "-"


def hosting_text(recipe: dict[str, Any]) -> str:
    """Where the full converted data lives.

    Examples
    --------
    >>> hosting_text({"hosting": {"full": {"location": "producer", "url": "s3://b/x.zarr"}}})
    'producer: `s3://b/x.zarr`'
    >>> hosting_text({"hosting": {"full": {"location": "waterpark"}}})
    'waterpark (not yet available)'
    >>> hosting_text({})
    'undecided'
    """
    full: dict[str, Any] = (recipe.get("hosting") or {}).get("full") or {}
    location = full.get("location") or "undecided"
    if location == "undecided":
        return location
    url = full.get("url")
    return f"{location}: `{url}`" if url else f"{location} (not yet available)"


def _location(recipe: dict[str, Any]) -> str:
    full: dict[str, Any] = (recipe.get("hosting") or {}).get("full") or {}
    return str(full.get("location") or "undecided")


def subset_text(recipe: dict[str, Any]) -> str:
    """Describe the optional Waterpark subset.

    Examples
    --------
    >>> subset = {"url": "s3://b/s.zarr", "description": "tas, pr at zoom 8"}
    >>> subset_text({"hosting": {"waterpark_subset": subset}})
    '`s3://b/s.zarr` (tas, pr at zoom 8)'
    >>> subset_text({"hosting": {"waterpark_subset": {"description": "planned: tas"}}})
    'planned: tas'
    >>> subset_text({})
    '-'
    """
    subset: dict[str, Any] = (recipe.get("hosting") or {}).get("waterpark_subset") or {}
    url, desc = subset.get("url"), subset.get("description")
    if url:
        return f"`{url}` ({desc})" if desc else f"`{url}`"
    return _cell(desc)


def metadata_table(recipe: dict[str, Any]) -> str:
    """Markdown table with the most important recipe fields.

    Examples
    --------
    >>> print(
    ...     metadata_table(
    ...         {
    ...             "issue": 7,
    ...             "license": "CC-BY-4.0",
    ...             "source": {"grid": "icon"},
    ...             "target": {"min_zoom": 0, "max_zoom": 9, "variables": ["tas"]},
    ...         }
    ...     )
    ... )
    | | |
    |---|---|
    | Data offer | [#7](https://github.com/km-scale/data-forge/issues/7) |
    | Maintainers | - |
    | License | CC-BY-4.0 |
    | Source | - |
    | Source grid | icon |
    | Source format | - |
    | Native resolution | - |
    | Zoom levels | 0 to 9 |
    | Variables | `tas` |
    | Chunks at max zoom | - |
    | Period | - |
    | Full data | undecided |
    | Waterpark subset | - |
    """
    src: dict[str, Any] = recipe.get("source") or {}
    tgt: dict[str, Any] = recipe.get("target") or {}
    issue = recipe.get("issue")
    issue_link = f"[#{issue}]({REPO}/issues/{issue})" if isinstance(issue, int) and issue > 0 else "-"
    rows = [
        ("Data offer", issue_link),
        ("Maintainers", _cell(recipe.get("maintainers"))),
        ("License", _cell(recipe.get("license"))),
        ("Source", _cell(src.get("description"))),
        ("Source grid", _cell(src.get("grid"))),
        ("Source format", _cell(src.get("format"))),
        ("Native resolution", _cell(src.get("native_resolution"))),
        ("Zoom levels", f"{tgt.get('min_zoom', '?')} to {tgt.get('max_zoom', '?')}"),
        ("Variables", _cell(tgt.get("variables"))),
        ("Chunks at max zoom", _cell(tgt.get("chunks"))),
        ("Period", period_text(recipe)),
        ("Full data", hosting_text(recipe)),
        ("Waterpark subset", subset_text(recipe)),
    ]
    return "\n".join(["| | |", "|---|---|", *(f"| {k} | {v} |" for k, v in rows)])


def recipe_page(folder: Path) -> str:
    """Full Markdown page for one recipe folder.

    Examples
    --------
    >>> page = recipe_page(RECIPES / "_template")
    >>> page.splitlines()[0]
    '# Recipe template'
    >>> "| `to_healpix` | Return ``ds`` on HEALPix nest" in page, '=== "convert.py"' in page
    (True, True)
    """
    recipe: dict[str, Any] = yaml.safe_load((folder / "recipe.yaml").read_text()) or {}
    is_template = folder.name == TEMPLATE
    parts = ["# Recipe template" if is_template else f"# {recipe.get('name', folder.name)}", ""]
    if is_template:
        parts += [
            '!!! tip "Start a new recipe"',
            "    Run `pixi run new-recipe <name>`, set `issue` in `recipe.yaml`, "
            "then adapt `open_source()` and `to_healpix()` in `convert.py`.",
            "",
        ]
    parts += [metadata_table(recipe), ""]

    readme = folder / "README.md"
    if readme.is_file() and not is_template:
        parts += [readme_body(readme.read_text()), ""]

    convert = folder / "convert.py"
    if convert.is_file():
        funcs = function_summary(convert.read_text())
        if funcs:
            parts += ["## Functions", "", "| Function | Purpose |", "|---|---|"]
            parts += [f"| `{name}` | {_cell(doc)} |" for name, doc in funcs]
            parts.append("")

    parts += ["## Source", ""]
    for name, lang in SOURCE_TABS:
        path = folder / name
        if path.is_file():
            parts += [f'=== "{name}"', "", code_block(path.read_text(), lang, indent="    "), ""]
    parts.append(f"[:octicons-mark-github-16: View folder on GitHub]({REPO}/tree/main/recipes/{folder.name})")
    return "\n".join(parts) + "\n"


def index_page(folders: Iterable[Path]) -> str:
    """Overview page with one table row per recipe.

    Examples
    --------
    >>> print(index_page([]).splitlines()[-1])
    No recipes yet. Start with the [template](template.md).
    """
    rows = []
    for folder in folders:
        r: dict[str, Any] = yaml.safe_load((folder / "recipe.yaml").read_text()) or {}
        tgt: dict[str, Any] = r.get("target") or {}
        src: dict[str, Any] = r.get("source") or {}
        issue = r.get("issue")
        rows.append(
            f"| [{folder.name}]({slug(folder)}.md) | {_cell(src.get('grid'))} "
            f"| {tgt.get('min_zoom', '?')} to {tgt.get('max_zoom', '?')} "
            f"| {_cell(tgt.get('variables'))} "
            f"| {_location(r)}{' + Waterpark subset' if subset_text(r) != '-' else ''} "
            f"| {f'[#{issue}]({REPO}/issues/{issue})' if issue else '-'} |"
        )
    parts = [
        "# Recipes",
        "",
        "Each recipe converts one dataset into the HEALPix Zarr v3 layout of the hackathon.",
        "The converted data lives with the producer, on Waterpark, or both (e.g. a subset on Waterpark).",
        "New recipes start from the [template](template.md).",
        "",
    ]
    if rows:
        parts += [
            "| Recipe | Source grid | Zoom | Variables | Hosting | Data offer |",
            "|---|---|---|---|---|---|",
            *rows,
        ]
    else:
        parts.append("No recipes yet. Start with the [template](template.md).")
    return "\n".join(parts)


def recipe_folders() -> list[Path]:
    """Recipe folders in display order, template excluded.

    Examples
    --------
    >>> all(f.name != "_template" for f in recipe_folders())
    True
    """
    return sorted(d for d in RECIPES.iterdir() if d.is_dir() and d.name != TEMPLATE)


def main() -> None:
    """Write all generated pages into the mkdocs build."""
    import mkdocs_gen_files  # noqa: PLC0415 - only available during the docs build

    folders = recipe_folders()
    with mkdocs_gen_files.open("recipes/index.md", "w") as f:
        f.write(index_page(folders))
    summary = ["* [Overview](index.md)", "* [Template](template.md)"]
    for folder in [RECIPES / TEMPLATE, *folders]:
        page = f"recipes/{slug(folder)}.md"
        with mkdocs_gen_files.open(page, "w") as f:
            f.write(recipe_page(folder))
        mkdocs_gen_files.set_edit_path(page, folder.relative_to(ROOT) / "recipe.yaml")
        if folder.name != TEMPLATE:
            summary.append(f"* [{folder.name}]({slug(folder)}.md)")
    with mkdocs_gen_files.open("recipes/SUMMARY.md", "w") as f:
        f.write("\n".join(summary) + "\n")

    tool_nav = []
    for tool in TOOLS:
        page = f"tools/{tool}.md"
        with mkdocs_gen_files.open(page, "w") as f:
            f.write(f"# {tool}.py\n\n::: {tool}\n")
        mkdocs_gen_files.set_edit_path(page, Path("scripts") / f"{tool}.py")
        tool_nav.append(f"* [{tool}.py]({tool}.md)")
    with mkdocs_gen_files.open("tools/SUMMARY.md", "w") as f:
        f.write("\n".join(tool_nav) + "\n")


if __name__ in {"__main__", "<run_path>"}:
    main()
