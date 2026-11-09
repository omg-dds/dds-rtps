#!/bin/bash

# Default values
input="."
publisher=""
subscriber=""
output=""
discovery_only=false
skip_discovery=false
single_test=""
sniffer_duration=""

# Function to display usage information
usage() {
    echo "Run the interoperability_report script for the specified applications."
    echo "If a publisher/subscriber is provided only that publisher/subscriber"
    echo "is used as a publisher or subscriber application. If a publisher or"
    echo "subscriber is not provided, this script will find and use all "
    echo "'*_shape_main_linux' applications in the input directory as publisher and"
    echo "subscribers."
    echo "Usage: $0 [-p publisher] [-s subscriber] [-o output] [-i input] [-d] [-t test] [-h]"
    echo "Options:"
    echo "  -p, --publisher         Specify the publisher application"
    echo "  -s, --subscriber        Specify the subscriber application"
    echo "  -o, --output            Specify the output XML file"
    echo "  -i, --input             Specify the directory where publisher/subscriber applications are located (only if -p and -s are not provided)"
    echo "  -d, --discovery-only    Run only the discovery test case (Test_Domain_0) to quickly verify RTPS discovery"
    echo "  -t, --test              Specify a single test case to run (e.g. Test_Domain_0)"
    echo "  --skip-discovery        Skip running RTPS discovery sniffer"
    echo "  --sniffer-duration      Capture duration in seconds for sniffer (default: 15, or 6 for discovery-only)"
    echo "  -h, --help              Print this help message"
    echo "Examples:"
    echo "Run Connext as publisher and all executables under './executables' as subscribers"
    echo "  ./run_tests.sh -p connext_dds-6.1.2_shape_main_linux -i ./executables"
    echo "Run discovery test only between Connext and Cyclone DDS:"
    echo "  ./run_tests.sh -p connext_dds-7.7.0_shape_main_linux -s eclipse_cyclone-11.0.1_shape_main_linux -d"
    exit 1
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--publisher)
            publisher="$2"
            shift 2
            ;;
        -s|--subscriber)
            subscriber="$2"
            shift 2
            ;;
        -o|--output)
            output="$2"
            shift 2
            ;;
        -i|--input)
            input="$2"
            shift 2
            ;;
        -d|--discovery-only)
            discovery_only=true
            shift 1
            ;;
        -t|--test)
            single_test="$2"
            shift 2
            ;;
        --skip-discovery)
            skip_discovery=true
            shift 1
            ;;
        --sniffer-duration)
            sniffer_duration="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Error: Unknown option $1"
            usage
            ;;
    esac
done

# If publisher is not provided, find publisher applications
if [[ -z $publisher ]]; then
    echo "Searching for publisher applications in directory: $input"
    publisher=$(find "$input" -type f -name '*shape_main_linux')
fi

# If subscriber is not provided, find subscriber applications
if [[ -z $subscriber ]]; then
    echo "Searching for subscriber applications in directory: $input"
    subscriber=$(find "$input" -type f -name '*shape_main_linux')
fi

# Check if required options are provided
if [[ -z $publisher || -z $subscriber ]]; then
    echo "Error: Unable to find publisher or subscriber applications."
    usage
fi

# Archive previous test results if present
archive_dir="./archive_reports"
shopt -s nullglob
old_reports=(*.xml *.xlsx index.html discovery_report_*.json discovery_summary.json timestamp)
if [ ${#old_reports[@]} -gt 0 ]; then
    echo "Archiving previous test reports to $archive_dir..."
    mkdir -p "$archive_dir"
    mv "${old_reports[@]}" "$archive_dir/" 2>/dev/null || true
fi
shopt -u nullglob
rm -f ./timestamp

# Run the application logic
for i in $publisher; do
    for j in $subscriber; do
        publisher_name=$(basename "$i" _shape_main_linux)
        subscriber_name=$(basename "$j" _shape_main_linux)
        echo "Testing Publisher $publisher_name --- Subscriber $subscriber_name"

        # Generate fresh timestamp for this test run in %Y%m%d-%H_%M_%S format
        # matching interoperability_report.py (e.g. 20260922-18_14_23)
        if [[ -f "./timestamp" ]]; then
            raw_ts=$(head -n 1 ./timestamp | tr -d '\r\n')
            if [[ "$raw_ts" =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})-(.*)$ ]]; then
                pair_timestamp="${BASH_REMATCH[1]}${BASH_REMATCH[2]}${BASH_REMATCH[3]}-${BASH_REMATCH[4]}"
            else
                pair_timestamp="$raw_ts"
            fi
        else
            pair_timestamp=$(date '+%Y%m%d-%H_%M_%S')
        fi

        # Synchronize interoperability report filename and discovery report filename
        if [[ -n $output ]]; then
            interop_report_file="$output"
        else
            interop_report_file="${publisher_name}-${subscriber_name}-${pair_timestamp}.xml"
        fi

        discovery_xml="junit_discovery_report_${pair_timestamp}.xml"
        discovery_json="discovery_report_${pair_timestamp}.json"

        extra_args=""
        if [[ "${subscriber_name,,}" == *opendds* && "${publisher_name,,}" == *connext_dds* ]]; then
            extra_args="--periodic-announcement 5000"
        fi;
        if [[ -n $single_test ]]; then
            extra_args="$extra_args -t $single_test"
        elif [[ "$discovery_only" == "true" ]]; then
            extra_args="$extra_args -t Test_Domain_0"
        fi;

        sniffer_pid=""

        if [[ "$skip_discovery" != "true" ]]; then
            dur=${sniffer_duration:-15}
            if [[ "$discovery_only" == "true" ]]; then
                dur=${sniffer_duration:-6}
            fi
            echo "Starting RTPS discovery sniffer for $publisher_name vs $subscriber_name (${dur}s)..."
            python3 ./rtps_discovery_sniffer.py \
                -i any \
                -d "$dur" \
                -P "$publisher_name" \
                -S "$subscriber_name" \
                -o "$discovery_xml" \
                -j "$discovery_json" \
                -t "$pair_timestamp" &
            sniffer_pid=$!
            # Give sniffer half a second to initialize capture on interface
            sleep 1
        fi

        python3 ./interoperability_report.py -P "$i" -S "$j" -o "$interop_report_file" $extra_args

        if [[ -n $sniffer_pid ]]; then
            echo "Waiting for RTPS discovery sniffer to finish..."
            wait "$sniffer_pid" 2>/dev/null || true
        fi

        if [ -d "./OpenDDS-durable-data-dir" ]; then
            echo Deleting OpenDDS-durable-data-dir;
            rm -rf ./OpenDDS-durable-data-dir;
        fi;
    done
done
