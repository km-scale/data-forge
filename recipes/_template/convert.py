#!/usr/bin/env python3
"""Conversion recipe template: source data -> HEALPix (nest) Zarr v3 pyramid.

Usage
-----
    python convert.py --recipe recipe.yaml --input "/path/to/files/*.nc" --output out.zarr
    python convert.py --recipe recipe.yaml --input ... --output s3://bucket/x.zarr \
        --endpoint-url https://s3.example.org

Only ``open_source`` and ``to_healpix`` are dataset specific. Everything else
(grid mapping, pyramid, chunking, writing) follows the hackathon conventions and
should normally stay as it is, so all recipes produce the same layout::

    out.zarr/
      z<max_zoom>/   finest level, from to_healpix
      ...
      z<min_zoom>/   coarsest level, averaged from the next finer one

Run on the sample first, then check the result::

    python ../../scripts/validate_healpix_zarr.py out.zarr -v
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
import yaml
import zarr

CELL = "cell"

# Reference ellipsoid (WGS84). Adjust here if the final guidelines say otherwise.
ELLIPSOID = {"semi_major_axis": 6378137.0, "inverse_flattening": 298.257223563}

Recipe = dict[str, Any]


def _demo(zoom: int = 1, dim: str = CELL) -> xr.Dataset:
    """Small HEALPix dataset used in the examples."""
    npix = 12 * 4**zoom
    return xr.Dataset(
        {"tas": (("time", dim), np.arange(2 * npix, dtype="f4").reshape(2, npix), {"units": "K"})},
        coords={"time": np.array(["2020-01-01T00", "2020-01-01T06"], dtype="datetime64[ns]")},
    )


_DEMO_RECIPE: Recipe = {
    "name": "demo",
    "license": "CC-BY-4.0",
    "source": {"grid": "healpix"},
    "target": {"max_zoom": 1, "min_zoom": 0, "variables": ["tas"], "chunks": {"time": 1, "cell": 12}},
}


# --------------------------------------------------------------------------
# Dataset specific: adapt these two functions
# --------------------------------------------------------------------------


def open_source(path: str, recipe: Recipe) -> xr.Dataset:
    """Open the input data lazily and select the variables to convert.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     _demo(dim="ncells").to_netcdf(f"{d}/in.nc")
    ...     ds = open_source(f"{d}/*.nc", _DEMO_RECIPE)
    ...     list(ds.data_vars), ds.sizes["ncells"]
    (['tas'], 48)
    """
    ds = xr.open_mfdataset(path, combine="by_coords", chunks={}, decode_timedelta=True)
    variables: list[str] = list(recipe["target"]["variables"])
    return ds[variables]


def to_healpix(ds: xr.Dataset, zoom: int, recipe: Recipe) -> xr.Dataset:
    """Return ``ds`` on HEALPix nest at ``zoom`` with dimension ``cell`` last.

    For HEALPix input this only checks and renames. For any other grid, put the
    remapping here, e.g. with grid-doctor (weights computed once, applied lazily).

    Examples
    --------
    >>> to_healpix(_demo(dim="ncells"), 1, _DEMO_RECIPE)["tas"].dims
    ('time', 'cell')
    >>> to_healpix(_demo(), 1, {"source": {"grid": "icon"}})
    Traceback (most recent call last):
    NotImplementedError: Remapping from 'icon' to HEALPix is not implemented yet. Add it in to_healpix().
    """
    grid = recipe["source"]["grid"]
    if grid != "healpix":
        msg = f"Remapping from '{grid}' to HEALPix is not implemented yet. Add it in to_healpix()."
        raise NotImplementedError(msg)
    npix = 12 * 4**zoom
    cdim = next((str(d) for d in ds.dims if ds.sizes[d] == npix), None)
    if cdim is None:
        msg = f"no dimension with {npix} cells for zoom {zoom}"
        raise ValueError(msg)
    if cdim != CELL:
        ds = ds.rename({cdim: CELL})
    # If the input is in ring order, convert to nest here.
    return ds.transpose(..., CELL)


# --------------------------------------------------------------------------
# Generic part: normally no changes needed below
# --------------------------------------------------------------------------


def add_grid_mapping(ds: xr.Dataset, zoom: int) -> xr.Dataset:
    """Attach the HEALPix grid mapping variable and cell coordinate.

    Examples
    --------
    >>> out = add_grid_mapping(_demo(), 1)
    >>> out["crs"].attrs["healpix_nside"], out["tas"].attrs["grid_mapping"], int(out.cell[-1])
    (2, 'crs', 47)
    """
    crs = xr.DataArray(
        0,
        attrs={
            "grid_mapping_name": "healpix",
            "healpix_nside": 2**zoom,
            "healpix_order": "nest",
            **ELLIPSOID,
        },
    )
    ds = ds.assign(crs=crs)
    for v in ds.data_vars:
        if CELL in ds[v].dims:
            ds[v].attrs["grid_mapping"] = "crs"
    if CELL not in ds.coords:
        ds = ds.assign_coords({CELL: np.arange(ds.sizes[CELL])})
    return ds


def coarsen_one_level(ds: xr.Dataset) -> xr.Dataset:
    """Average groups of 4 nest-ordered children into their parent cell.

    Examples
    --------
    >>> coarse = coarsen_one_level(add_grid_mapping(_demo(zoom=1), 1))
    >>> coarse.sizes[CELL], coarse["tas"].values[0, :3].tolist()
    (12, [1.5, 5.5, 9.5])
    """
    out = ds.drop_vars([CELL, "crs"], errors="ignore")
    return out.coarsen({CELL: 4}).mean(keep_attrs=True)


def encoding_for(ds: xr.Dataset, chunks: dict[str, int]) -> dict[str, dict[str, Any]]:
    """Zarr encoding with chunk sizes per variable, capped at the dimension sizes.

    Examples
    --------
    >>> encoding_for(_demo(zoom=1), {"time": 24, "cell": 16})
    {'tas': {'chunks': (2, 16)}}
    """
    enc: dict[str, dict[str, Any]] = {}
    for v in ds.data_vars:
        dims = [str(d) for d in ds[v].dims]
        if CELL in dims:
            enc[str(v)] = {"chunks": tuple(min(chunks.get(d, ds.sizes[d]), ds.sizes[d]) for d in dims)}
    return enc


def convert(recipe: Recipe, source: str, output: str, storage_options: dict[str, Any] | None = None) -> None:
    """Run the whole recipe: open, remap, write all zoom levels.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     _demo(zoom=1, dim="ncells").to_netcdf(f"{d}/in.nc")
    ...     convert(_DEMO_RECIPE, f"{d}/in.nc", f"{d}/out.zarr")
    ...     sorted(name for name, _ in zarr.open_group(f"{d}/out.zarr", mode="r").groups())
    wrote z1: 48 cells
    wrote z0: 12 cells
    ['z0', 'z1']
    """
    tgt = recipe["target"]
    zmax, zmin = int(tgt["max_zoom"]), int(tgt["min_zoom"])
    chunks: dict[str, int] = dict(tgt.get("chunks", {}))

    ds = to_healpix(open_source(source, recipe), zmax, recipe)
    ds.attrs.setdefault("license", recipe.get("license", ""))
    ds.attrs["recipe"] = f"km-scale/data-forge recipes/{recipe['name']}"

    for zoom in range(zmax, zmin - 1, -1):
        level = add_grid_mapping(ds, zoom)
        lvl_chunks = {**chunks, CELL: min(chunks.get(CELL, level.sizes[CELL]), level.sizes[CELL])}
        first = next(iter(level.data_vars))
        level = level.chunk({str(d): lvl_chunks.get(str(d), -1) for d in level[first].dims})
        level.to_zarr(
            output,
            group=f"z{zoom}",
            mode="w",
            zarr_format=3,
            consolidated=False,
            encoding=encoding_for(level, lvl_chunks),
            storage_options=storage_options,
        )
        print(f"wrote z{zoom}: {level.sizes[CELL]} cells")
        if zoom > zmin:
            # read back what was just written, so coarser levels don't recompute the remap
            written = xr.open_zarr(
                output, group=f"z{zoom}", zarr_format=3, consolidated=False, storage_options=storage_options
            )
            ds = coarsen_one_level(written)

    root = zarr.open_group(output, mode="a", storage_options=storage_options)
    root.attrs.update({str(k): v for k, v in ds.attrs.items() if isinstance(v, str | int | float)})


def main() -> None:
    """Command line entry point."""
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    p.add_argument("--recipe", default="recipe.yaml", type=Path)
    p.add_argument("--input", required=True, help="input path or glob")
    p.add_argument("--output", required=True, help="output Zarr store (path or s3://)")
    p.add_argument("--endpoint-url", help="S3 endpoint for the output")
    args = p.parse_args()

    with args.recipe.open() as f:
        recipe: Recipe = yaml.safe_load(f)
    opts = {"client_kwargs": {"endpoint_url": args.endpoint_url}} if args.endpoint_url else None
    convert(recipe, args.input, args.output, opts)


if __name__ == "__main__":
    main()
