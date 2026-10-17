<!-- For a new or changed recipe. Other changes: replace this text with a short description. -->

## Recipe

Data offer: #<!-- issue number -->
Recipe folder: `recipes/<name>/`

## Checklist

- [ ] Folder copied from `recipes/_template/`, `name` in `recipe.yaml` matches the folder
- [ ] `issue` in `recipe.yaml` points to the data-offer issue
- [ ] Ran `convert.py` on the sample
- [ ] `just ci` passes locally (lint, strict typing, doctests for every public function)
- [ ] `requirements.txt` of the recipe lists everything it needs, with versions pinned
- [ ] `scripts/validate_healpix_zarr.py` passes on the sample output
- [ ] `sample_output.url` set (if the sample is readable anonymously) so CI can validate it
- [ ] README filled in: input location pattern, run command, resources used
- [ ] No credentials, internal hostnames or embargoed details in the PR

## Notes for reviewers

<!-- Remapping choices, open questions, things you are unsure about. -->
