#!/bin/bash
# ==============================================================================
# Run DDS-RTPS interoperability tests inside an isolated Docker container
# Workflow:
#   1. Archives any existing reports from host into archive_reports/
#   2. Starts Docker container
#   3. Runs the test suite inside the container
#   4. Generates XML, XLSX, and HTML reports
#   5. Exits and cleans up Docker container automatically
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="dds-rtps-tester"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: 'docker' command not found. Please install Docker first."
    exit 1
fi

# 1. Archive previous test reports from host if present
archive_dir="$SCRIPT_DIR/archive_reports"
shopt -s nullglob
old_reports=("$SCRIPT_DIR"/*.xml "$SCRIPT_DIR"/*.xlsx "$SCRIPT_DIR"/index.html)
if [ ${#old_reports[@]} -gt 0 ]; then
    echo "==> [1/4] Archiving previous test reports to archive_reports/..."
    mkdir -p "$archive_dir"
    mv "${old_reports[@]}" "$archive_dir/" 2>/dev/null || true
fi
shopt -u nullglob

# 2. Build Docker image if not present
if [[ "$(docker images -q "$IMAGE_NAME" 2> /dev/null)" == "" ]]; then
    echo "==> [2/4] Building Docker image: $IMAGE_NAME..."
    docker build -t "$IMAGE_NAME" .
fi

# Determine test arguments: default to all executables under ./executables
if [ $# -eq 0 ]; then
    TEST_CMD="./run_tests.sh -i ./executables"
else
    TEST_CMD="./run_tests.sh $*"
fi

echo "==> [3/4] Running tests inside Docker container ($IMAGE_NAME)..."
echo "    Command: $TEST_CMD"

# 3. Run container, execute tests, generate reports, and automatically terminate container (--rm)
docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$SCRIPT_DIR:/workspace" \
    -w /workspace \
    "$IMAGE_NAME" \
    /bin/bash -c "$TEST_CMD; ./generate_reports.sh"

echo ""
echo "==> [4/4] Docker container finished and closed."
echo "==> Generated reports in $SCRIPT_DIR:"
ls -lh "$SCRIPT_DIR"/junit_interoperability_report.xml "$SCRIPT_DIR"/interoperability_report.xlsx "$SCRIPT_DIR"/index.html 2>/dev/null || true
