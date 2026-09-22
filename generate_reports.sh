#!/bin/bash
set -e

# Change to script directory
cd "$(dirname "$0")"

# Remove previously merged XML report and Excel report to avoid conflict
rm -f junit_interoperability_report.xml interoperability_report.xlsx

echo "[1/3] Merging XML reports into junit_interoperability_report.xml..."
reports_to_merge=()
shopt -s nullglob
for f in *.xml; do
    if [[ "$f" != "junit_interoperability_report.xml" && "$f" != junit_discovery_report* ]]; then
        reports_to_merge+=("$f")
    fi
done
shopt -u nullglob

if [ ${#reports_to_merge[@]} -gt 0 ]; then
    python3 -m junitparser merge "${reports_to_merge[@]}" junit_interoperability_report.xml
fi

echo "[2/3] Generating Excel report interoperability_report.xlsx..."
python3 generate_xlsx_report.py --input junit_interoperability_report.xml --output interoperability_report.xlsx

echo "[3/3] Generating HTML report index.html..."
if command -v xunit-viewer &> /dev/null; then
    xunit-viewer --results=./junit_interoperability_report.xml --output=./index.html
else
    npx -y xunit-viewer --results=./junit_interoperability_report.xml --output=./index.html
fi

echo "Done! Generated reports:"
ls -lh junit_interoperability_report.xml interoperability_report.xlsx index.html 2>/dev/null || true
