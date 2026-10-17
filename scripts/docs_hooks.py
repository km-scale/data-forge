"""MkDocs hooks for the documentation site.

Registered in ``mkdocs.yml`` under ``hooks``.
"""

from __future__ import annotations

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import event_priority
from mkdocs.structure.files import Files

NAV_FILE = "SUMMARY.md"


@event_priority(-110)  # after literate-nav (-100) has read the nav files
def on_files(files: Files, config: MkDocsConfig) -> Files:  # noqa: ARG001 - hook signature
    """Drop the generated nav files so they are not rendered as pages.

    Examples
    --------
    >>> from mkdocs.structure.files import File
    >>> fs = Files(
    ...     [
    ...         File(p, "docs", "site", use_directory_urls=True)
    ...         for p in ("index.md", "recipes/SUMMARY.md", "recipes/x.md")
    ...     ]
    ... )
    >>> [f.src_uri for f in on_files(fs, None)]  # type: ignore[arg-type]
    ['index.md', 'recipes/x.md']
    """
    for f in [f for f in files if f.src_uri.rsplit("/", 1)[-1] == NAV_FILE]:
        files.remove(f)
    return files
