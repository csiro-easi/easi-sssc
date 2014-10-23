#!/bin/sh

# Pass the URL of the service as the first parameter
url="$1"

probid=$(curl "$1/problems" -d @tcrm-problem.json -X POST -H "Content-Type: application/json")

echo "Inserted TCRM problem: $probid"

tboxid=$(curl "$1/toolboxes" -d @tcrm-toolbox.json -X POST -H "Content-Type: application/json")

echo "Inserted TCRM toolbox: $tboxid"

solutionid=$(curl "$1/solutions?tbox=$tboxid&problem=$probid" -d @tcrm-solution.json -X POST -H "Content-Type: application/json")

echo "Inserted TCRM solution: $solutionid"

probid=$(curl "$1/problems" -d @anuga-problem.json -X POST -H "Content-Type: application/json")

echo "Inserted ANUGA problem: $probid"

tboxid=$(curl "$1/toolboxes" -d @anuga-toolbox.json -X POST -H "Content-Type: application/json")

echo "Inserted ANUGA toolbox: $tboxid"

solutionid=$(curl "$1/solutions?tbox=$tboxid&problem=$probid" -d @anuga-solution.json -X POST -H "Content-Type: application/json")

echo "Inserted ANUGA solution: $solutionid"
