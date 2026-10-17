<!--
Body for the pinned tracking issue.
Title suggestion: "📊 Hackathon 2027 datasets: offers, wishes and status"
Labels: tracking · Milestone: Hackathon 2027
After creating it, store its number in the repo variable DATASET_TRACKING_ISSUE.
Do not remove the offers/wishes start and end markers below: the lists between them are generated.
-->

This issue collects **all datasets planned for the June 2027 hackathon**. It shows what is already available, what is being prepared and what people would like to analyse. Datasets are provided as **HEALPix (ellipsoidal) in Zarr v3 via S3**, hosted by the producers, on [Waterpark](https://waterpark.dkrz.de) where space allows, or both.

## How to take part

| You are… | Do this |
|---|---|
| **Producing / holding data** you'd like to provide | Open a [📦 data offer](https://github.com/km-scale/data-forge/issues/new?template=01-data-offer.yml) |
| **Hoping to analyse** a dataset that isn't listed | Open a [🙋 data wish](https://github.com/km-scale/data-forge/issues/new?template=02-data-wish.yml), or 👍 an existing one |
| Just following | Subscribe to this issue and watch the [project board](https://github.com/orgs/km-scale/projects/3) |

Each dataset gets **its own issue**, which is linked here automatically. Please keep discussion in the dataset's issue rather than in this one.

## Workflow

1. **Proposed**: offer issue opened.
2. **Sample received**: you send a few time steps (all variables) to DKRZ. Arranged privately via **waterpark@support.dkrz.de**, subject `[data-forge #<issue>] <dataset>`.
3. **Recipe drafted**: we write a conversion recipe (`recipes/<name>/`) from the sample, in a pull request linked to the issue.
4. **Handed over**: you run it on the full dataset (we help where needed).
5. **Validated**: output passes `validate_healpix_zarr.py`.
6. **Available**: readable at its final location (producer endpoint, Waterpark, or an important subset on Waterpark). The issue is closed and ticked below.

Status of every dataset is shown on the [project board](https://github.com/orgs/km-scale/projects/3).

**Public vs. private:** design questions, conventions and conversion problems that others can learn from belong in GitHub. Upload routes, credentials, internal paths and embargoed details go to the support desk.

See the [data provision guidelines](https://github.com/km-scale/data-forge/blob/main/docs/data-provision.md) for formats and conventions.

## Timeline

- **YYYY-MM-DD**: deadline for data offers
- **YYYY-MM-DD**: deadline for samples at DKRZ
- **YYYY-MM-DD**: full datasets converted and validated
- **June 2027**: hackathon

## Already available

_Maintained by the data team._

- [x] Dataset A (S3 location)
- [x] Dataset B (S3 location)

## Offered datasets

_Ticked = available. Generated automatically, do not edit by hand._

<!-- offers:start -->
<!-- offers:end -->

## Dataset wishes

_Ticked = fulfilled. Generated automatically, do not edit by hand. Please 👍 the wishes you share._

<!-- wishes:start -->
<!-- wishes:end -->
