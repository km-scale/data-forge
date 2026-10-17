# Getting datasets ready for km-scale hackathons

Data producers offer datasets, scientists ask for the data
they want to analyse, and conversion **recipes** turn model output into HEALPix (nest, ellipsoidal) Zarr v3,
ideally readable via S3, hosted by the producers, or on [Waterpark](https://waterpark.dkrz.de) where space allows, or both.

<div class="grid cards" markdown>

-   :material-package-variant-plus: **Provide a dataset**

    ---

    Open a data offer. We draft a recipe from a small sample, you run it on the full data.

    [:octicons-arrow-right-24: Data offer](https://github.com/km-scale/data-forge/issues/new?template=01-data-offer.yml)

-   :material-hand-wave: **Ask for a dataset**

    ---

    Missing something for your analysis? Open a wish or 👍 an existing one.

    [:octicons-arrow-right-24: Data wish](https://github.com/km-scale/data-forge/issues/new?template=02-data-wish.yml)

-   :material-anvil: **Browse recipes**

    ---

    Every conversion, with its metadata, notes and code.

    [:octicons-arrow-right-24: Recipes](recipes/index.md)

-   :material-check-decagram: **Validate your output**

    ---

    Check a store against the conventions before making it available.

    [:octicons-arrow-right-24: Validator](tools/validate_healpix_zarr.md)

</div>

## How a dataset gets here

1. **Offer**: open a data-offer issue. It appears in the tracking issue and on the project board.
2. **Sample**: send a few time steps with all variables. The upload route is arranged privately via
   `waterpark@support.dkrz.de` with `[data-forge #<issue>]` in the subject.
3. **Recipe**: we draft `recipes/<name>/` from the sample, in a pull request linked to the issue.
4. **Run**: you run the recipe on the full dataset, close to where the data lives.
5. **Validate**: the validator must pass.
6. **Make it available**: the validated data goes to its final location (your S3 endpoint - if available, Waterpark, or an
   important subset on Waterpark) and the issue is closed.

The details are in [Data provision](data-provision.md).
