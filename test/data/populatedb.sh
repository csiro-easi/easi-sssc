#!/bin/sh

# Pass the URL of the service as the first parameter
url="$1"

tboxid=$(curl "$1/toolboxes" -d @tcrm-toolbox.json -X POST -H "Content-Type: application/json")

echo "Inserted TCRM toolbox: $tboxid"

solutionid=$(curl "$1/solutions?tbox=$tboxid" -d @tcrm-solution.json -X POST -H "Content-Type: application/json")

echo "Inserted TCRM solution: $solutionid"

tboxid=$(curl "$1/toolboxes" -d @anuga-toolbox.json -X POST -H "Content-Type: application/json")

echo "Inserted ANUGA toolbox: $tboxid"

solutionid=$(curl "$1/solutions?tbox=$tboxid" -d @anuga-solution.json -X POST -H "Content-Type: application/json")

echo "Inserted ANUGA solution: $solutionid"
