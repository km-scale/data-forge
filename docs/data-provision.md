# Data provision guidelines

How to get a dataset ready for the hackathon (June 2027). 
Ideally converted datasets are read via S3, either from the 
producer's own endpoint or from [Waterpark](https://waterpark.dkrz.de), DKRZ's HEALPix / Zarr / S3 data hub.
Hosting on Waterpark depends on available space. Where the full dataset doesn't fit, an important subset can
go to Waterpark instead.

> Conventions marked **(draft)** are still being agreed with the organisers. Check back before
> running a full conversion. The validator is updated alongside this page.

## 1. Target format

| Aspect | Requirement |
|---|---|
| Storage format | **Zarr v3** |
| Grid | **HEALPix**, `nest` indexing, on the reference ellipsoid **(draft: exact ellipsoid and latitude convention)** |
| Grid description | A scalar grid mapping variable (e.g. `crs`) with `grid_mapping_name: healpix`, the resolution (`healpix_nside` or `refinement_level`), the indexing scheme and the ellipsoid parameters **(draft: attribute names)** |
| Cell dimension | Named `cell`, last dimension of every variable. Full sphere: `12 · nside²` cells. Regional data: a `cell` coordinate with the HEALPix indices |
| Resolution pyramid | One group per zoom level (`z0`, `z1`, … up to native), coarser levels by averaging **(draft: which levels are mandatory)** |
| Metadata | CF-style: `units` (required), `standard_name` or `long_name`, `grid_mapping` on every data variable. Global `title`, `institution`, `source`, `license`, `references` |
| Time | Monotonic, no duplicates, CF-encoded |
| Chunking | Roughly 16 to 256 MiB uncompressed per chunk. Use Zarr v3 sharding to keep object counts on S3 manageable |
| Access | If the data can be served from an object store: anonymous read: your own endpoint, Waterpark (if space allows), or both (e.g. a subset on Waterpark) |

## 2. Workflow

1. **Open a [data offer](https://github.com/km-scale/data-forge/issues/new?template=01-data-offer.yml)**. It is linked to the
   dataset tracking issue and the project board automatically.
2. **Email `waterpark@support.dkrz.de`** with subject `[data-forge #<issue>] <dataset>`. This creates a support
   ticket where we arrange how the sample gets to DKRZ. Credentials and internal paths stay there, never on GitHub.
3. **Send a sample**: all variables, all vertical levels and output frequencies you plan to provide,
   but only **a few time steps**. Keep it small (a few GB is ideal).
4. **We draft a conversion recipe** (`recipes/<name>/`) from the sample in a pull request linked to your issue, and hand it over to you
   with instructions.
5. **You run the full conversion** close to your data. Tell us early (`needs-conversion-help`) if compute or
   people are a problem.
6. **Validate** the output:

   ```console
   pixi run validate my-data.zarr
   ```

   The dataset is ready when it reports `PASSED` without errors.
7. **Make it available**: the validated store goes to its final location (your object store endpoint - if available, Waterpark, or an
   important subset on Waterpark) and is recorded under `hosting` in `recipe.yaml`. The issue is closed and
   ticked in the tracking issue. Listing the dataset in the hackathon catalogue is handled by the organisers.

## 3. What goes where

| Topic | Where |
|---|---|
| What data will be available, wishes, priorities | GitHub (tracking issue, dataset issues) |
| Conventions, conversion problems others can learn from | GitHub (dataset issue) |
| Sample upload, credentials, storage quotas, internal paths, embargoed details | `waterpark@support.dkrz.de` |
| Status of each dataset | Project board |

## 4. Deadlines

See the timeline in the pinned tracking issue.
