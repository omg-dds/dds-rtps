#!/usr/bin/env python3
"""
Unit tests for rtps_discovery_sniffer.py
Tests decoding functions, parsing of discovery traffic, and JUnit XML report generation.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

import junitparser
import rtps_discovery_sniffer as sniffer


class TestRTPSDiscoverySniffer(unittest.TestCase):

    def test_vendor_decoding(self):
        self.assertEqual(sniffer.decode_vendor("010f"), ("01.0f", "eProsima Fast DDS"))
        self.assertEqual(sniffer.decode_vendor("0110"), ("01.10", "Eclipse Cyclone DDS"))
        self.assertEqual(sniffer.decode_vendor("0101"), ("01.01", "RTI Connext DDS"))
        self.assertEqual(sniffer.decode_vendor("0105"), ("01.05", "Twin Oaks CoreDX DDS"))
        self.assertEqual(sniffer.decode_vendor("0114"), ("01.14", "Dust DDS"))
        self.assertEqual(sniffer.decode_vendor("0103"), ("01.03", "OpenDDS"))
        self.assertEqual(sniffer.decode_vendor("0x010f"), ("01.0f", "eProsima Fast DDS"))

    def test_version_decoding(self):
        self.assertEqual(sniffer.decode_version("0x0204"), "2.4")
        self.assertEqual(sniffer.decode_version("0x0202"), "2.2")
        self.assertEqual(sniffer.decode_version("0x0201"), "2.1")
        self.assertEqual(sniffer.decode_version(0x0204), "2.4")

    def test_builtin_endpoints_decoding(self):
        mask_hex, flags = sniffer.decode_builtin_endpoints("0x0000003f")
        self.assertEqual(mask_hex, "0x0000003f")
        self.assertIn("DISC_BUILTIN_ENDPOINT_PARTICIPANT_ANNOUNCER", flags)
        self.assertIn("DISC_BUILTIN_ENDPOINT_PARTICIPANT_DETECTOR", flags)
        self.assertIn("DISC_BUILTIN_ENDPOINT_PUBLICATION_ANNOUNCER", flags)
        self.assertIn("DISC_BUILTIN_ENDPOINT_PUBLICATION_DETECTOR", flags)
        self.assertIn("DISC_BUILTIN_ENDPOINT_SUBSCRIPTION_ANNOUNCER", flags)
        self.assertIn("DISC_BUILTIN_ENDPOINT_SUBSCRIPTION_DETECTOR", flags)

    def test_timestamp_selection(self):
        # 1. Without timestamp file
        ts1 = sniffer.get_current_timestamp()
        self.assertRegex(ts1, r"^\d{8}-\d{2}_\d{2}_\d{2}$")

        # 2. With timestamp file
        ts_file = Path("timestamp")
        was_present = ts_file.exists()
        original_content = ts_file.read_text() if was_present else None
        try:
            ts_file.write_text("20260916-20_09_43\n")
            self.assertEqual(sniffer.get_current_timestamp(), "20260916-20_09_43")
            # Also test normalization from YYYY-MM-DD
            ts_file.write_text("2026-09-16-20_09_43\n")
            self.assertEqual(sniffer.get_current_timestamp(), "20260916-20_09_43")
        finally:
            if was_present and original_content is not None:
                ts_file.write_text(original_content)
            elif ts_file.exists():
                ts_file.unlink()

    def test_junit_report_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_xml = os.path.join(tmpdir, "junit_discovery_report_test.xml")
            sample_summary = {
                "metadata": {"total_rtps_packets": 20},
                "participants": {
                    "010ff34897b8c87f00000000": {
                        "guid_prefix": "010ff34897b8c87f00000000",
                        "src_ip": "192.168.1.10",
                        "vendor_id": "01.0f",
                        "vendor_name": "eProsima Fast DDS",
                        "protocol_version": "2.2",
                        "lease_duration_sec": 20.0,
                        "builtin_endpoints_mask": "0x00000c3f",
                        "builtin_endpoints_flags": ["DISC_BUILTIN_ENDPOINT_PARTICIPANT_ANNOUNCER"],
                        "locators": [{"type": "unicast", "ip": "192.168.1.10", "port": 7410}],
                    },
                    "0110f34897b8c87f00000000": {
                        "guid_prefix": "0110f34897b8c87f00000000",
                        "src_ip": "192.168.1.20",
                        "vendor_id": "01.10",
                        "vendor_name": "Eclipse Cyclone DDS",
                        "protocol_version": "2.3",
                        "lease_duration_sec": 20.0,
                        "builtin_endpoints_mask": "0x00000c3f",
                        "builtin_endpoints_flags": ["DISC_BUILTIN_ENDPOINT_PARTICIPANT_ANNOUNCER"],
                        "locators": [{"type": "unicast", "ip": "192.168.1.20", "port": 7412}],
                    },
                },
                "endpoints": [
                    {
                        "endpoint_guid": "010ff34897b8c87f0000000000000102",
                        "entity_kind": "DataWriter",
                        "topic_name": "Square",
                        "type_name": "ShapeType",
                        "reliability": "RELIABLE",
                        "durability": "VOLATILE",
                        "ownership": "SHARED",
                        "src_ip": "192.168.1.10",
                    },
                    {
                        "endpoint_guid": "0110f34897b8c87f0000000000000107",
                        "entity_kind": "DataReader",
                        "topic_name": "Square",
                        "type_name": "ShapeType",
                        "reliability": "RELIABLE",
                        "durability": "VOLATILE",
                        "ownership": "SHARED",
                        "src_ip": "192.168.1.20",
                    },
                ],
            }

            xml = sniffer.generate_junit_report(
                summary=sample_summary,
                output_xml_path=out_xml,
                publisher_name="fastdds",
                subscriber_name="cyclone",
                expected_participants=2,
                expected_topic="Square",
                expected_type="ShapeType",
            )

            self.assertTrue(os.path.exists(out_xml))
            read_xml = junitparser.JUnitXml.fromfile(out_xml)
            suites = list(read_xml)
            self.assertEqual(len(suites), 1)
            suite = suites[0]
            self.assertEqual(suite.name, "rtps_discovery_fastdds---cyclone")
            self.assertEqual(suite.tests, 7)
            self.assertEqual(suite.failures, 0)
            self.assertEqual(suite.errors, 0)

    def test_qos_incompatibility_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_xml = os.path.join(tmpdir, "junit_discovery_report_fail.xml")
            sample_summary = {
                "metadata": {"total_rtps_packets": 20},
                "participants": {
                    "010ff34897b8c87f00000000": {
                        "guid_prefix": "010ff34897b8c87f00000000",
                        "vendor_id": "01.0f",
                        "vendor_name": "eProsima Fast DDS",
                        "protocol_version": "2.2",
                    },
                    "0110f34897b8c87f00000000": {
                        "guid_prefix": "0110f34897b8c87f00000000",
                        "vendor_id": "01.10",
                        "vendor_name": "Eclipse Cyclone DDS",
                        "protocol_version": "2.3",
                    },
                },
                "endpoints": [
                    {
                        "endpoint_guid": "010ff34897b8c87f0000000000000102",
                        "entity_kind": "DataWriter",
                        "topic_name": "Square",
                        "type_name": "ShapeType",
                        "reliability": "BEST_EFFORT",
                        "durability": "VOLATILE",
                    },
                    {
                        "endpoint_guid": "0110f34897b8c87f0000000000000107",
                        "entity_kind": "DataReader",
                        "topic_name": "Square",
                        "type_name": "ShapeType",
                        "reliability": "RELIABLE",  # Incompatible with BEST_EFFORT writer!
                        "durability": "VOLATILE",
                    },
                ],
            }

            sniffer.generate_junit_report(
                summary=sample_summary,
                output_xml_path=out_xml,
            )

            read_xml = junitparser.JUnitXml.fromfile(out_xml)
            suite = list(read_xml)[0]
            self.assertEqual(suite.failures, 1)


if __name__ == "__main__":
    unittest.main()
