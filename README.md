# dds-rtps

Validation of interoperability of products compliant with [OMG DDS-RTPS standard](http://www.omg.org/spec/DDSI-RTPS/). This is considered one of the core [DDS Specifications](http://portals.omg.org/dds/omg-dds-standard/). See http://portals.omg.org/dds/ for an overview of DDS.

The executables found on the [release tab of this repository](https://github.com/omg-dds/dds-rtps/releases) test discovery, DDS Topic and QoS matching, and interoperability for different QoS settings. The goal is to validate that the implementations perform these functions in compliance with OMG DDS-RTPS standard and can interoperate with each other.

# Interoperability Automatic Tests

The script `interoperability_report.py` generates automatically
the verification between two executables of these interoperability tests.
The tests that the script runs must be defined previosly (for example
`test_suite.py`).
Once the script finishes, it generates a report with the result
of the interoperability tests between both executables.

## Options of interoperability_report

The `interoperability_report.py` may configure the following options:

```
$ python3 interoperability_report.py -h

usage: interoperability_report.py [-h] -P publisher_name -S subscriber_name
                                  [-v] [-f {junit,csv,xlxs}] [-o filename]
Interoperability Test
optional arguments:
  -h, --help            show this help message and exit
general options:
  -P publisher_name, --publisher publisher_name
                        Publisher Shape Application
  -S subscriber_name, --subscriber subscriber_name
                        Subscriber Shape Application
optional parameters:
  -v, --verbose         Print more information to stdout.
output options:
  -f {junit,csv,xlxs}, --output-format {junit,csv,xlxs}
                        Output format.
  -o filename, --output-name filename
                        Report filename.
```

**NOTE**: The option -f only supports junit.

### Example of use interoperability_report

This is an example that runs the `interoperability_report.py`
with the test suite `test_suite.py`

```
$ python3 interoperability_report.py -P <path_to_publisher_executable> -S <path_to_subscriber_executable>
```

This generates a report file in JUnit (xml) with the name of both executables
used, the date and the time in which it was generated. For example:
`<executable_name_publisher>-<executable_name_subscriber>-20230117-16_49_42.xml`

## Requirements

- Python 3.8+
- Create and enable a virtual environment (installing requirements)

## Using virtual environments

The build will be done using virtual environments, you should create and
activate the virtual environment and then install all dependencies. This can be
done by following these steps:

### Create virtual environment

In Linux® systems, you may need to install the corresponding python venv
package:

```
sudo apt install python3.8-venv
```

To create the virtual environment:

```
python3 -m venv .venv
```

### Activate virtual environment

```
source .venv/bin/activate
```

### Install requirements

This step is only required the first time or when the requirements change:

```
pip install -r requirements.txt
```
