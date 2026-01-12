#!/bin/bash

# Default values
input="."
publisher=""
subscriber=""
output=""

# Function to display usage information
usage() {
    echo "Run the interoperability_report script for the specified applications."
    echo "If a publisher/subscriber is provided only that publisher/subscriber"
    echo "is used as a publisher or subscriber application. If a publisher or"
    echo "subscriber is not provided, this script will find and use all "
    echo "'*_shape_main_linux' applications in the input directory as publisher and"
    echo "subscribers."
    echo "Usage: $0 [-p publisher] [-s subscriber] [-o output] [-i input] [-h]"
    echo "Options:"
    echo "  -p, --publisher   Specify the publisher application"
    echo "  -s, --subscriber  Specify the subscriber application"
    echo "  -o, --output      Specify the output XML file"
    echo "  -i, --input       Specify the directory where publisher/subscriber applications are located (only if -p and -s are not provided)"
    echo "  -h, --help        Print this help message"
    echo "Examples:"
    echo "Run Connext as publisher and all executables under './executables' as subscribers"
    echo "  ./run_tests.sh -p connext_dds-6.1.2_shape_main_linux -i ./executables"
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

# Run the application logic
for i in $publisher; do
    for j in $subscriber; do
        publisher_name=$(basename "$i" _shape_main_linux)
        subscriber_name=$(basename "$j" _shape_main_linux)
        echo "Testing Publisher $publisher_name --- Subscriber $subscriber_name"
        extra_args=""
        if [[ "${subscriber_name,,}" == *opendds* && "${publisher_name,,}" == *connext_dds* ]]; then
            extra_args="--periodic-announcement 5000"
        fi;
        if [[ -n $output ]]; then
            python3 ./interoperability_report.py -P "$i" -S "$j" -o "$output" $extra_args
        else
            python3 ./interoperability_report.py -P "$i" -S "$j" $extra_args
        fi
        if [ -d "./OpenDDS-durable-data-dir" ]; then
            echo Deleting OpenDDS-durable-data-dir;
            rm -rf ./OpenDDS-durable-data-dir;
        fi;
    done
done
