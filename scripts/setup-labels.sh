#!/usr/bin/env bash
# Create or update the labels used by data-forge (issues, recipes, PRs).
# Usage: ./scripts/setup-labels.sh km-scale/data-forge
set -euo pipefail
REPO="${1:?usage: $0 km-scale/data-forge}"

label() { gh label create "$1" --repo "$REPO" --color "$2" --description "$3" --force; }

label "dataset"               "0E8A16" "Dataset offer or request for the hackathon"
label "data-offer"            "1D76DB" "A producer offers a dataset"
label "data-wish"             "C5DEF5" "Someone would like to analyse a dataset"
label "tracking"              "5319E7" "Tracking / overview issue"
label "needs-conversion-help" "D93F0B" "Producer cannot run the full conversion alone"
label "blocked"               "B60205" "Waiting on something outside our control"
label "size:S"                "EDEDED" "< 1 TB"
label "size:M"                "D4D4D4" "1 - 10 TB"
label "size:L"                "BDBDBD" "10 - 100 TB"
label "size:XL"               "9E9E9E" "100 TB - 1 PB"
label "size:XXL"              "616161" "> 1 PB"
label "recipe"                "FBCA04" "Adds or changes a conversion recipe"
