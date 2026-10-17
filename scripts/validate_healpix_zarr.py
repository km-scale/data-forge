#!/usr/bin/env python3
"""Check a HEALPix Zarr v3 store against the hackathon data conventions.

Usage
-----
    python validate_healpix_zarr.py /path/to/store.zarr
    python validate_healpix_zarr.py s3://bucket/store.zarr --endpoint-url https://s3.example.org --anon

The store may hold a single zoom level (data variables at the root) or one
child group per zoom level (e.g. ``z0/``, ``z1/`` ... or ``zoom_8/``).

Exit code is 1 if any ERROR was found (or any WARN with ``--strict``).

The conventions are still being finalised. Everything that may change is
collected in ``CONVENTION`` below, so adapt it there rather than in the checks.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Callable, Hashable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import xarray as xr
import zarr


@dataclass(frozen=True)
class Convention:
    """All convention details the validator checks against.

    Examples
    --------
    >>> Convention().required_order
    'nest'
    >>> Convention(cell_dim="ncells").cell_dim
    'ncells'
    """

    cell_dim: str = "cell"
    grid_mapping_name: str = "healpix"
    nside_attrs: tuple[str, ...] = ("healpix_nside",)
    level_attrs: tuple[str, ...] = ("refinement_level", "healpix_level", "zoom")
    order_attrs: tuple[str, ...] = ("healpix_order", "indexing_scheme")
    required_order: str = "nest"
    ellipsoid_attr_sets: tuple[tuple[str, ...], ...] = (
        ("semi_major_axis", "inverse_flattening"),
        ("semi_major_axis", "semi_minor_axis"),
        ("reference_ellipsoid_name",),
    )
    recommended_global_attrs: tuple[str, ...] = ("title", "institution", "source", "license", "references")
    required_var_attrs: tuple[str, ...] = ("units",)
    # at least one attribute of each tuple
    recommended_var_attrs: tuple[tuple[str, ...], ...] = (("standard_name", "long_name"),)
    # uncompressed chunk size window in MiB (warning only)
    chunk_mib: tuple[float, float] = (1.0, 256.0)


CONVENTION = Convention()

Attrs = Mapping[Hashable, Any]


@dataclass
class Report:
    """Collects findings, grouped by severity.

    Examples
    --------
    >>> r = Report()
    >>> r.error("z3", "bad")
    >>> r.warn("z3:tas", "meh")
    >>> r.errors, r.warnings, r.failed(strict=False), r.failed(strict=True)
    (['[z3] bad'], ['[z3:tas] meh'], True, True)
    >>> Report(warnings=["x"]).failed(strict=False)
    False
    """

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    def error(self, where: str, msg: str) -> None:
        """Record an error.

        >>> r = Report()
        >>> r.error("/", "x")
        >>> r.errors
        ['[/] x']
        """
        self.errors.append(f"[{where}] {msg}")

    def warn(self, where: str, msg: str) -> None:
        """Record a warning.

        >>> r = Report()
        >>> r.warn("/", "x")
        >>> r.warnings
        ['[/] x']
        """
        self.warnings.append(f"[{where}] {msg}")

    def info(self, where: str, msg: str) -> None:
        """Record an informational line.

        >>> r = Report()
        >>> r.info("/", "x")
        >>> r.infos
        ['[/] x']
        """
        self.infos.append(f"[{where}] {msg}")

    def failed(self, strict: bool) -> bool:
        """Whether the report counts as failed.

        >>> Report(errors=["e"]).failed(strict=False)
        True
        """
        return bool(self.errors) or (strict and bool(self.warnings))


def _demo(zoom: int = 1, ellipsoid: bool = True, order: str = "nest") -> xr.Dataset:
    """Small valid HEALPix dataset used in the examples."""
    nside = 2**zoom
    npix = 12 * nside * nside
    crs: dict[str, Any] = {"grid_mapping_name": "healpix", "healpix_nside": nside, "healpix_order": order}
    if ellipsoid:
        crs |= {"semi_major_axis": 6378137.0, "inverse_flattening": 298.257223563}
    return xr.Dataset(
        {
            "tas": (
                ("time", "cell"),
                np.zeros((2, npix), dtype="f4"),
                {"units": "K", "standard_name": "air_temperature", "grid_mapping": "crs"},
            ),
            "crs": ((), 0, crs),
        },
        coords={
            "time": np.array(["2020-01-01T00", "2020-01-01T06"], dtype="datetime64[ns]"),
            "cell": np.arange(npix),
        },
    )


def _first(attrs: Attrs, names: tuple[str, ...]) -> tuple[str | None, Any]:
    for n in names:
        if n in attrs:
            return n, attrs[n]
    return None, None


def find_grid_mapping(ds: xr.Dataset, rep: Report, where: str) -> tuple[str | None, Attrs | None]:
    """Find the HEALPix grid mapping variable.

    Examples
    --------
    >>> r = Report()
    >>> name, attrs = find_grid_mapping(_demo(), r, "/")
    >>> name, attrs["healpix_order"], r.errors
    ('crs', 'nest', [])
    >>> find_grid_mapping(_demo().drop_vars("crs"), r, "/")
    (None, None)
    >>> r.errors
    ["[/] no variable with grid_mapping_name='healpix' (e.g. a scalar 'crs' variable)"]
    """
    gm_name = CONVENTION.grid_mapping_name
    cands = [str(n) for n, v in ds.variables.items() if v.attrs.get("grid_mapping_name") == gm_name]
    if not cands:
        rep.error(where, f"no variable with grid_mapping_name='{gm_name}' (e.g. a scalar 'crs' variable)")
        return None, None
    if len(cands) > 1:
        rep.warn(where, f"several HEALPix grid mapping variables: {cands}; using '{cands[0]}'")
    return cands[0], ds[cands[0]].attrs


def check_grid_mapping(attrs: Attrs, rep: Report, where: str, allow_spherical: bool) -> int | None:
    """Check resolution, indexing and ellipsoid; return nside.

    Examples
    --------
    >>> r = Report()
    >>> check_grid_mapping(_demo(zoom=3)["crs"].attrs, r, "/", allow_spherical=False)
    8
    >>> r.errors
    []
    >>> check_grid_mapping({"refinement_level": 2, "indexing_scheme": "ring"}, r, "/", allow_spherical=False)
    4
    >>> r.errors
    ["[/] indexing_scheme='ring', expected 'nest'",
     '[/] no reference ellipsoid described in grid mapping (looks spherical)']
    """
    nside: int | None = None
    key, val = _first(attrs, CONVENTION.nside_attrs)
    if key is not None:
        nside = int(val)
    else:
        key, val = _first(attrs, CONVENTION.level_attrs)
        if key is not None:
            nside = 2 ** int(val)
    if nside is None:
        rep.error(where, f"grid mapping lacks resolution ({CONVENTION.nside_attrs + CONVENTION.level_attrs})")
    elif nside < 1 or nside & (nside - 1):
        rep.error(where, f"nside={nside} is not a power of two")
    else:
        rep.info(where, f"nside={nside} (zoom {int(math.log2(nside))})")

    key, order = _first(attrs, CONVENTION.order_attrs)
    if key is None:
        rep.error(where, f"grid mapping lacks indexing scheme ({CONVENTION.order_attrs})")
    elif str(order).lower() != CONVENTION.required_order:
        rep.error(where, f"{key}='{order}', expected '{CONVENTION.required_order}'")

    has_ellipsoid = any(all(a in attrs for a in s) for s in CONVENTION.ellipsoid_attr_sets)
    if not has_ellipsoid:
        report: Callable[[str, str], None] = rep.warn if allow_spherical else rep.error
        report(where, "no reference ellipsoid described in grid mapping (looks spherical)")
    return nside


def check_cells(ds: xr.Dataset, nside: int | None, rep: Report, where: str) -> None:
    """Check the cell dimension against nside, including regional subsets.

    Examples
    --------
    >>> r = Report()
    >>> check_cells(_demo(zoom=1), 2, r, "/")
    >>> r.errors
    []
    >>> regional = _demo(zoom=1).isel(cell=slice(0, 10))
    >>> check_cells(regional, 2, r, "/")
    >>> r.errors, r.infos
    ([], ['[/] regional subset: 10 of 48 cells (20.8 %)'])
    >>> check_cells(_demo(zoom=1), 1, r, "/")
    >>> r.errors
    ["[/] 'cell' has 48 entries but nside=1 allows only 12"]
    """
    cdim = CONVENTION.cell_dim
    if cdim not in ds.dims:
        rep.error(where, f"no '{cdim}' dimension (dims: {list(ds.dims)})")
        return
    n = ds.sizes[cdim]
    if nside is None:
        return
    npix = 12 * nside * nside
    has_coord = cdim in ds.coords
    if n == npix:
        if has_coord and not np.array_equal(ds[cdim].values, np.arange(npix)):
            rep.error(where, f"'{cdim}' coordinate is not 0..{npix - 1} in order")
        return
    if n > npix:
        rep.error(where, f"'{cdim}' has {n} entries but nside={nside} allows only {npix}")
        return
    if not has_coord:
        rep.error(where, f"'{cdim}' has {n} of {npix} cells but no '{cdim}' coordinate with the cell indices")
        return
    vals = ds[cdim].values
    if vals.min() < 0 or vals.max() >= npix:
        rep.error(where, f"'{cdim}' indices out of range 0..{npix - 1}")
    elif np.any(np.diff(vals) <= 0):
        rep.warn(where, f"'{cdim}' indices of the regional subset are not strictly increasing")
    else:
        rep.info(where, f"regional subset: {n} of {npix} cells ({100 * n / npix:.1f} %)")


def check_time(ds: xr.Dataset, rep: Report, where: str) -> None:
    """Check that time is present, increasing and free of duplicates.

    Examples
    --------
    >>> r = Report()
    >>> check_time(_demo(), r, "/")
    >>> r.errors
    []
    >>> backwards = _demo().isel(time=[1, 0])
    >>> check_time(backwards, r, "/")
    >>> r.errors
    ['[/] time is not monotonically increasing']
    """
    if "time" not in ds.coords:
        rep.warn(where, "no 'time' coordinate")
        return
    t = ds["time"].values
    if t.size > 1:
        d = np.diff(t)
        zero = d[0] * 0  # works for numpy timedelta64 and cftime/datetime.timedelta
        if np.any(d == zero):
            rep.error(where, "duplicate time steps")
        if np.any(d < zero):
            rep.error(where, "time is not monotonically increasing")
    rep.info(where, f"time: {t[0]} .. {t[-1]} ({t.size} steps)")


def check_variables(
    ds: xr.Dataset, zgroup: zarr.Group | None, gm_var: str | None, rep: Report, where: str
) -> None:
    """Check attributes, dimension order and chunk sizes of the data variables.

    ``zgroup`` gives access to the stored chunk layout; pass ``None`` to skip chunk checks.

    Examples
    --------
    >>> r = Report()
    >>> check_variables(_demo(), None, "crs", r, "/")
    >>> r.errors, r.warnings
    ([], [])
    >>> ds = _demo()
    >>> del ds["tas"].attrs["units"]
    >>> check_variables(ds.transpose("cell", "time"), None, "crs", r, "/")
    >>> r.errors
    ["[/:tas] missing attribute 'units'"]
    >>> r.warnings
    ["[/:tas] 'cell' is not the last dimension ('cell', 'time'); this hurts spatial chunking"]
    """
    cdim = CONVENTION.cell_dim
    lo, hi = CONVENTION.chunk_mib
    data_vars = [str(v) for v in ds.data_vars if cdim in ds[v].dims]
    if not data_vars:
        rep.error(where, f"no data variables on the '{cdim}' dimension")
    for name in data_vars:
        v = ds[name]
        w = f"{where}:{name}"
        for a in CONVENTION.required_var_attrs:
            if a not in v.attrs:
                rep.error(w, f"missing attribute '{a}'")
        for alts in CONVENTION.recommended_var_attrs:
            if not any(a in v.attrs for a in alts):
                rep.warn(w, f"missing one of {alts}")
        gm = v.attrs.get("grid_mapping") or v.encoding.get("grid_mapping")
        if gm_var and gm != gm_var:
            rep.warn(w, f"grid_mapping attribute is {gm!r}, expected {gm_var!r}")
        if v.dims[-1] != cdim:
            rep.warn(w, f"'{cdim}' is not the last dimension {v.dims}; this hurts spatial chunking")
        if zgroup is None or name not in zgroup:
            continue
        arr = zgroup[name]
        if not isinstance(arr, zarr.Array):
            continue
        mib = float(np.prod(arr.chunks)) * arr.dtype.itemsize / 2**20
        extra = f", shards {arr.shards}" if arr.shards else ""
        rep.info(w, f"chunks {arr.chunks} = {mib:.1f} MiB uncompressed{extra}")
        if mib < lo:
            rep.warn(w, f"chunks are small ({mib:.2f} MiB < {lo:g} MiB): many objects on S3")
        elif mib > hi:
            rep.warn(w, f"chunks are large ({mib:.0f} MiB > {hi:g} MiB): slow partial reads")


def validate_store(
    store: str, storage_options: dict[str, Any] | None = None, allow_spherical: bool = False
) -> Report:
    """Validate a whole store (all zoom groups) and return the report.

    Examples
    --------
    >>> import tempfile
    >>> with tempfile.TemporaryDirectory() as d:
    ...     _ = _demo(zoom=2).to_zarr(f"{d}/s.zarr", group="z2", zarr_format=3, consolidated=False)
    ...     r = validate_store(f"{d}/s.zarr")
    >>> r.errors
    []
    >>> [w for w in r.warnings if "global" in w][:1]
    ["[/] missing global attribute 'title'"]
    """
    rep = Report()
    try:
        root = zarr.open_group(store, mode="r", storage_options=storage_options)
    except Exception as e:  # noqa: BLE001 - any failure to open is a finding
        rep.error("/", f"cannot open store: {e}")
        return rep

    if root.metadata.zarr_format != 3:
        rep.error("/", f"zarr_format is {root.metadata.zarr_format}, expected 3")
    for a in CONVENTION.recommended_global_attrs:
        if a not in root.attrs:
            rep.warn("/", f"missing global attribute '{a}'")

    root_has_cells = any(
        CONVENTION.cell_dim in (getattr(a.metadata, "dimension_names", None) or ()) for _, a in root.arrays()
    )
    levels: list[str | None] = (
        [None] if root_has_cells else list[str | None](sorted(name for name, _ in root.groups()))
    )
    if not levels:
        rep.error("/", "no HEALPix data at the root and no child groups")

    for lvl in levels:
        where = lvl or "/"
        try:
            ds = xr.open_zarr(
                store,
                group=lvl,
                zarr_format=3,
                consolidated=False,
                storage_options=storage_options,
                chunks=None,
                decode_timedelta=True,
            )
        except Exception as e:  # noqa: BLE001
            rep.error(where, f"could not open with xarray: {e}")
            continue
        zgroup = root[lvl] if lvl else root
        gm_var, gm_attrs = find_grid_mapping(ds, rep, where)
        nside = check_grid_mapping(gm_attrs, rep, where, allow_spherical) if gm_attrs is not None else None
        check_cells(ds, nside, rep, where)
        check_time(ds, rep, where)
        check_variables(ds, zgroup if isinstance(zgroup, zarr.Group) else None, gm_var, rep, where)
    return rep


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    p.add_argument("store", help="local path or s3:// URL of the Zarr store")
    p.add_argument("--endpoint-url", help="S3 endpoint URL")
    p.add_argument("--anon", action="store_true", help="anonymous S3 access")
    p.add_argument("--allow-spherical", action="store_true", help="only warn if no ellipsoid is described")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    p.add_argument("-v", "--verbose", action="store_true", help="also print info lines")
    args = p.parse_args(argv)

    opts: dict[str, Any] = {}
    if args.store.startswith("s3://"):
        if args.anon:
            opts["anon"] = True
        if args.endpoint_url:
            opts["client_kwargs"] = {"endpoint_url": args.endpoint_url}

    rep = validate_store(args.store, opts or None, args.allow_spherical)
    if args.verbose:
        for m in rep.infos:
            print(f"INFO  {m}")
    for m in rep.warnings:
        print(f"WARN  {m}")
    for m in rep.errors:
        print(f"ERROR {m}")

    failed = rep.failed(args.strict)
    print(f"\n{'FAILED' if failed else 'PASSED'}: {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
