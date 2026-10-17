# Getting datasets ready for km-scale hackathons

This is where data producers offer datasets, scientists ask for
the data they want to analyse, and conversion recipes turn model output into
HEALPix (nest, ellipsoidal) Zarr v3.

> This is not a Python package. It is a place for coordination and a collection of conversion recipes.

## I want to…

| | |
|---|---|
| **provide a dataset** | Open a [📦 data offer](https://github.com/km-scale/data-forge/issues/new?template=01-data-offer.yml) |
| **analyse a dataset that isn't listed** | Open a [🙋 data wish](https://github.com/km-scale/data-forge/issues/new?template=02-data-wish.yml) or 👍 an existing one |
| **see what's planned** | Check the pinned tracking issue and the [project board](PROJECT_BOARD_URL) |
| **run or adapt a recipe** | Look in [`recipes/`](recipes/) |
| **ask something private** (upload data snippets) | Email `waterpark@support.dkrz.de` with `[data-forge #<issue>]` in the subject |

## How a dataset gets here

```
data offer (issue) ──► sample to DKRZ ──► recipe drafted (PR) ──► producer runs it ──► validated ──► available
                         private ticket     recipes/<name>/          on the full data     validator     via S3
```

1. **Offer**: open a data-offer issue. It appears in the tracking issue and on the board.
2. **Sample**: send a few time steps with all variables. The route is arranged via the support desk.
3. **Recipe**: we draft `recipes/<name>/` from the sample in a pull request linked to your issue.
4. **Run**: you run the recipe on the full dataset, close to where the data lives. We help where needed.
5. **Validate**: `scripts/validate_healpix_zarr.py` should pass.
6. **Make it available**: the validated data goes to its final location (e.g S3 endpoint, Waterpark, or an
   important subset on Waterpark) and the issue is closed.

Details on formats and conventions: [docs/data-provision.md](docs/data-provision.md)

## Repository layout

```
recipes/
  _template/          start here: recipe.yaml, convert.py, README.md, pixi.toml
  <dataset>/          one folder per dataset, each its own pixi workspace
scripts/
  validate_healpix_zarr.py   check a store against the conventions
  check_recipes.py           check recipe folders (used in CI)
  recipe_tasks.py            run typing and doctests in each recipe's environment
  new_recipe.py              copy the template for a new recipe
  check_doctests.py          every public function needs a doctest
  gen_docs.py, docs_hooks.py build the recipe pages of the site
docs/                 site pages (guidelines, landing page)
pixi.toml             environments and tasks, `pixi run ci`
```

Code is licensed BSD-3-Clause. Datasets produced by recipes are licensed by their producers,
see each recipe.

## Starting a recipe

Requires [pixi](https://pixi.sh). It installs Python and all dependencies from conda-forge.

> On NixOs: `nix develop --command data-forge <shell>`

```console
pixi run -e dev pre-commit autoupdate
pixi run new-recipe <dataset>   # copies the template
cd recipes/<dataset>
# set `issue` in recipe.yaml, adapt open_source() and to_healpix() in convert.py,
# add dependencies with `pixi add <package>` (or `pixi add --pypi <package>`)
pixi run convert "<sample files>" sample.zarr
pixi run validate sample.zarr
cd ../.. && pixi run ci         # everything CI runs
```

Each recipe has its own `pixi.lock`, so a conversion can be rerun later with exactly the same packages.


## Development

| Task | |
|---|---|
| `pixi run lint` / `pixi run fmt` | ruff lint and format check / auto-fix |
| `pixi run typecheck` | mypy `--strict` on `scripts/` |
| `pixi run doctest` | run the doctests of `scripts/` |
| `pixi run recipe-checks` | mypy `--strict` and doctests of every recipe, in its own environment |
| `pixi run doctest-coverage` | every public function must have a doctest example |
| `pixi run recipes` | check recipe folders, validate published samples |
| `pixi run docs` / `pixi run serve` | build the site (strict) / preview it locally |
| `pixi run ci` | all of the above |

`pixi task list` shows every task.



The site is published at **https://km-scale.github.io/data-forge/** and renders every recipe with its
metadata, notes and code.

Maintained by the DKRZ data team. Setup notes for maintainers: [SETUP.md](SETUP.md)
