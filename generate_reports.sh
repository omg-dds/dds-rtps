#!/bin/bash
set -e

# Change to script directory
cd "$(dirname "$0")"

# Remove previously merged XML report to avoid merging it into itself
rm -f junit_interoperability_report.xml

echo "[1/3] Merging XML reports into junit_interoperability_report.xml..."
python3 -m junitparser merge *.xml junit_interoperability_report.xml

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
