#!/bin/sh

# Pass the URL of the service as the first parameter
url="$1"

tboxid=$(curl "$1/toolboxes" -d @tcrmbox.json -X POST -H "Content-Type: application/json")

echo "Inserted TCRM toolbox: $tboxid"

templateid=$(curl "$1/templates?tbox=$tboxid" -d @tcrmtemplate.json -X POST -H "Content-Type: application/json")

echo "Inserted TCRM template: $templateid"
