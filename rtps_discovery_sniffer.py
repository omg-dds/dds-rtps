#!/usr/bin/env python3
"""
RTPS Discovery Sniffer & JUnit/JSON Report Generator
OMG DDS-RTPS Interoperability Testing Suite

Captures and parses RTPS discovery metatraffic (SPDP and SEDP ParameterLists in CDR format).
Extracts participant identity, runtime settings, endpoint topology, and QoS parameters.
Generates:
  - junit_discovery_report_<timestamp>.xml (JUnit XML for CI / test reporting)
  - discovery_report_<timestamp>.json (Structured JSON summary for jq / automated assertions)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import junitparser

# Known DDS Vendors mapping (RTPS VendorId)
# Standard vendor IDs registered with OMG
VENDOR_MAP: Dict[str, str] = {
    "0101": "RTI Connext DDS",
    "0102": "OpenSplice DDS",
    "0103": "OpenDDS",
    "0104": "MilSoft",
    "0105": "Twin Oaks CoreDX DDS",
    "0106": "Lakos",
    "0107": "PrismTech",
    "0108": "OAMAS",
    "0109": "THALES",
    "010a": "ATIS",
    "010f": "eProsima Fast DDS",
    "0110": "Eclipse Cyclone DDS",
    "0111": "GurumNetworks GurumDDS",
    "0112": "RustDDS",
    "0113": "Shadow Security DDS",
    "0114": "Dust DDS",
    "0120": "Intercom DDS",
}

# Builtin endpoint set bits (RTPS 2.5 Specification Table 9.4)
BUILTIN_ENDPOINTS_MAP = {
    0x00000001: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_ANNOUNCER",
    0x00000002: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_DETECTOR",
    0x00000004: "DISC_BUILTIN_ENDPOINT_PUBLICATION_ANNOUNCER",
    0x00000008: "DISC_BUILTIN_ENDPOINT_PUBLICATION_DETECTOR",
    0x00000010: "DISC_BUILTIN_ENDPOINT_SUBSCRIPTION_ANNOUNCER",
    0x00000020: "DISC_BUILTIN_ENDPOINT_SUBSCRIPTION_DETECTOR",
    0x00000040: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_PROXY_ANNOUNCER",
    0x00000080: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_PROXY_DETECTOR",
    0x00000100: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_STATE_ANNOUNCER",
    0x00000200: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_STATE_DETECTOR",
    0x00000400: "BUILTIN_ENDPOINT_PARTICIPANT_MESSAGE_DATA_WRITER",
    0x00000800: "BUILTIN_ENDPOINT_PARTICIPANT_MESSAGE_DATA_READER",
    0x00001000: "BITS_TYPE_LOOKUP_SERVICE_REQUEST_DATA_WRITER",
    0x00002000: "BITS_TYPE_LOOKUP_SERVICE_REQUEST_DATA_READER",
    0x00004000: "BITS_TYPE_LOOKUP_SERVICE_REPLY_DATA_WRITER",
    0x00008000: "BITS_TYPE_LOOKUP_SERVICE_REPLY_DATA_READER",
    0x00010000: "DISC_BUILTIN_ENDPOINT_PUBLICATION_SECURE_ANNOUNCER",
    0x00020000: "DISC_BUILTIN_ENDPOINT_PUBLICATION_SECURE_DETECTOR",
    0x00040000: "DISC_BUILTIN_ENDPOINT_SUBSCRIPTION_SECURE_ANNOUNCER",
    0x00080000: "DISC_BUILTIN_ENDPOINT_SUBSCRIPTION_SECURE_DETECTOR",
    0x00100000: "BUILTIN_ENDPOINT_PARTICIPANT_MESSAGE_SECURE_DATA_WRITER",
    0x00200000: "BUILTIN_ENDPOINT_PARTICIPANT_MESSAGE_SECURE_DATA_READER",
    0x00400000: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_SECURE_ANNOUNCER",
    0x00800000: "DISC_BUILTIN_ENDPOINT_PARTICIPANT_SECURE_DETECTOR",
}

RELIABILITY_KINDS = {
    1: "BEST_EFFORT",
    2: "RELIABLE",
}

DURABILITY_KINDS = {
    0: "VOLATILE",
    1: "TRANSIENT_LOCAL",
    2: "TRANSIENT",
    3: "PERSISTENT",
}

OWNERSHIP_KINDS = {
    0: "SHARED",
    1: "EXCLUSIVE",
}


def normalize_hex(val: Any, length: int = 4) -> str:
    """Normalize hex string or int to lowercase hex digits without '0x'."""
    if val is None:
        return ""
    if isinstance(val, int):
        return f"{val:0{length}x}"
    s = str(val).strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    s = s.replace(":", "").replace(".", "")
    return s.zfill(length)


def format_guid(raw_guid: Any) -> str:
    """Format GUID prefix or full GUID to clean hex string."""
    if not raw_guid:
        return "unknown"
    if isinstance(raw_guid, list):
        raw_guid = raw_guid[0]
    s = str(raw_guid).strip().lower().replace(":", "").replace(".", "")
    if s.startswith("0x"):
        s = s[2:]
    return s


def decode_vendor(vendor_val: Any) -> Tuple[str, str]:
    """Return (vendor_hex_id, vendor_human_name)."""
    norm = normalize_hex(vendor_val, length=4)
    name = VENDOR_MAP.get(norm, f"Unknown DDS Vendor ({norm})")
    formatted = f"{norm[:2]}.{norm[2:]}" if len(norm) == 4 else norm
    return formatted, name


def decode_version(ver_val: Any) -> str:
    """Decode protocol version from hex (e.g. 0x0204 -> 2.4)."""
    if ver_val is None:
        return "unknown"
    if isinstance(ver_val, (int, float)):
        val_int = int(ver_val)
        major = (val_int >> 8) & 0xFF
        minor = val_int & 0xFF
        return f"{major}.{minor}"
    s = str(ver_val).strip()
    if s.startswith("0x") and len(s) >= 6:
        try:
            val_int = int(s, 16)
            major = (val_int >> 8) & 0xFF
            minor = val_int & 0xFF
            return f"{major}.{minor}"
        except ValueError:
            pass
    return s


def decode_builtin_endpoints(mask_val: Any) -> Tuple[str, List[str]]:
    """Decode built-in endpoints bitmask into hex string and flag names."""
    if mask_val is None:
        return "0x00000000", []
    try:
        val_int = int(mask_val, 16) if isinstance(mask_val, str) else int(mask_val)
    except (ValueError, TypeError):
        return str(mask_val), []
    flags = [name for bit, name in BUILTIN_ENDPOINTS_MAP.items() if (val_int & bit) != 0]
    return f"0x{val_int:08x}", flags


def get_current_timestamp() -> str:
    """
    Get timestamp aligned with interoperability reports (%Y%m%d-%H_%M_%S).
    1. Read './timestamp' file if present.
    2. Fallback to current datetime '%Y%m%d-%H_%M_%S'.
    """
    timestamp_file = Path("timestamp")
    if timestamp_file.is_file():
        try:
            content = timestamp_file.read_text().strip()
            if content:
                m = re.match(r"^(\d{4})-(\d{2})-(\d{2})-(.*)$", content)
                if m:
                    return f"{m.group(1)}{m.group(2)}{m.group(3)}-{m.group(4)}"
                return content
        except Exception:
            pass
    return datetime.now().strftime("%Y%m%d-%H_%M_%S")


def capture_traffic_pcap(interface: str, duration_sec: int, output_pcap: str) -> bool:
    """Capture raw RTPS UDP packets to a pcap file using tshark."""
    if not shutil.which("tshark"):
        raise RuntimeError(
            "tshark is not installed. Install it via 'apt-get install -y tshark'."
        )

    cmd = [
        "tshark",
        "-i",
        interface,
        "-a",
        f"duration:{duration_sec}",
        "-f",
        "udp",
        "-w",
        output_pcap,
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=duration_sec + 10,
        )
        return os.path.exists(output_pcap) and os.path.getsize(output_pcap) > 0
    except subprocess.TimeoutExpired:
        return os.path.exists(output_pcap) and os.path.getsize(output_pcap) > 0


def dump_rtps_json_from_pcap(pcap_path: str) -> List[Dict[str, Any]]:
    """Dissect RTPS packets from pcap using tshark with full JSON output."""
    cmd = [
        "tshark",
        "--no-duplicate-keys",
        "-r",
        pcap_path,
        "-Y",
        "rtps",
        "-T",
        "json",
    ]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []


def parse_discovery_data(raw_packets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze JSON packets dissected by Wireshark RTPS dissector.
    Extracts:
      - Participants (SPDP): GUID prefix, IP, vendor ID, version, locators, lease, builtin endpoints
      - Endpoints (SEDP): Entity GUID, entity kind, topic name, type name, QoS parameters
    """
    summary: Dict[str, Any] = {
        "metadata": {
            "total_rtps_packets": len(raw_packets),
            "analyzed_at": datetime.now().isoformat(),
        },
        "participants": {},
        "endpoints": [],
    }

    def walk_tree(obj: Any, callback):
        """Recursively traverse the Wireshark dissection tree."""
        if isinstance(obj, dict):
            callback(obj)
            for v in obj.values():
                walk_tree(v, callback)
        elif isinstance(obj, list):
            for item in obj:
                walk_tree(item, callback)

    for pkt in raw_packets:
        source = pkt.get("_source", {})
        layers = source.get("layers", {})
        rtps = layers.get("rtps", {})
        ip_layer = layers.get("ip", {})
        src_ip = ip_layer.get("ip.src", layers.get("ip.src", "unknown"))
        dst_ip = ip_layer.get("ip.dst", layers.get("ip.dst", "unknown"))
        if isinstance(src_ip, list):
            src_ip = src_ip[0]
        if isinstance(dst_ip, list):
            dst_ip = dst_ip[0]

        # Extract Header fields
        header_guid = rtps.get("rtps.guidPrefix", rtps.get("rtps.guidPrefix.src"))
        header_vendor = rtps.get("rtps.vendorId")
        header_version = rtps.get("rtps.version")

        # ----------------------------------------------------
        # SPDP Participant Discovery Detection
        # ----------------------------------------------------
        # Look for PID_PARTICIPANT_GUID, PID_PROTOCOL_VERSION, PID_VENDOR_ID
        found_spdp: Dict[str, Any] = {}
        locators_found: List[Dict[str, Any]] = []

        def inspect_spdp_node(node: Dict[str, Any]):
            for k, v in node.items():
                k_lower = k.lower()

                # Participant GUID
                if "pid_participant_guid" in k_lower or k == "rtps.param.participant_guid":
                    guid_val = node.get("rtps.param.participant_guid", v)
                    guid_str = format_guid(guid_val)
                    # 12 bytes = 24 hex chars prefix
                    prefix = guid_str[:24] if len(guid_str) >= 24 else guid_str
                    found_spdp["guid_prefix"] = prefix

                # Vendor ID
                if "pid_vendor_id" in k_lower or k == "rtps.vendorId":
                    v_val = node.get("rtps.vendorId", v)
                    v_hex, v_name = decode_vendor(v_val)
                    found_spdp["vendor_id"] = v_hex
                    found_spdp["vendor_name"] = v_name

                # Protocol Version
                if "pid_protocol_version" in k_lower or k == "rtps.version":
                    ver_val = node.get("rtps.version", v)
                    found_spdp["protocol_version"] = decode_version(ver_val)

                # Lease Duration
                if "pid_participant_lease_duration" in k_lower or "lease_duration" in k_lower:
                    sec = node.get("rtps.param.ntpTime.sec")
                    if sec is not None:
                        try:
                            found_spdp["lease_duration_sec"] = float(sec)
                        except (ValueError, TypeError):
                            pass

                # Built-in endpoints
                if "pid_builtin_endpoint_set" in k_lower or "builtin_endpoint_set" in k_lower:
                    mask = node.get("rtps.param.builtin_endpoint_set", v)
                    mask_hex, flags = decode_builtin_endpoints(mask)
                    found_spdp["builtin_endpoints_mask"] = mask_hex
                    found_spdp["builtin_endpoints_flags"] = flags

                # Locators
                if "locator" in k_lower and isinstance(node, dict):
                    loc_ip = node.get("rtps.locator.ipv4") or node.get("rtps.locator_udp_v4.ip")
                    loc_port = node.get("rtps.locator.port") or node.get("rtps.locator_udp_v4.port")
                    if loc_ip and loc_port:
                        kind = "unicast"
                        if "metatraffic" in k_lower:
                            kind = "metatraffic_unicast"
                        elif "multicast" in k_lower:
                            kind = "multicast"
                        locators_found.append({
                            "type": kind,
                            "ip": str(loc_ip),
                            "port": int(str(loc_port).split()[0], 0) if str(loc_port).isdigit() or str(loc_port).startswith("0x") else str(loc_port),
                        })

        walk_tree(rtps, inspect_spdp_node)

        # Fallback to header values if parameter wasn't explicitly captured
        guid_p = found_spdp.get("guid_prefix") or (format_guid(header_guid)[:24] if header_guid else None)
        if guid_p and guid_p not in summary["participants"]:
            v_hex, v_name = decode_vendor(found_spdp.get("vendor_id") or header_vendor)
            proto_ver = found_spdp.get("protocol_version") or decode_version(header_version)
            unique_locs = []
            seen_locs = set()
            for loc in locators_found:
                lk = (loc["type"], loc["ip"], loc["port"])
                if lk not in seen_locs:
                    seen_locs.add(lk)
                    unique_locs.append(loc)
            summary["participants"][guid_p] = {
                "guid_prefix": guid_p,
                "src_ip": src_ip,
                "vendor_id": v_hex,
                "vendor_name": v_name,
                "protocol_version": proto_ver,
                "lease_duration_sec": found_spdp.get("lease_duration_sec", 20.0),
                "builtin_endpoints_mask": found_spdp.get("builtin_endpoints_mask", "unknown"),
                "builtin_endpoints_flags": found_spdp.get("builtin_endpoints_flags", []),
                "locators": unique_locs,
            }
        elif guid_p and guid_p in summary["participants"]:
            # Augment existing participant with newly seen locators or flags
            part = summary["participants"][guid_p]
            if not part.get("builtin_endpoints_flags") and found_spdp.get("builtin_endpoints_flags"):
                part["builtin_endpoints_mask"] = found_spdp["builtin_endpoints_mask"]
                part["builtin_endpoints_flags"] = found_spdp["builtin_endpoints_flags"]
            if found_spdp.get("lease_duration_sec"):
                part["lease_duration_sec"] = found_spdp["lease_duration_sec"]
            existing_locs = {(l["type"], l["ip"], l["port"]) for l in part["locators"]}
            for loc in locators_found:
                lk = (loc["type"], loc["ip"], loc["port"])
                if lk not in existing_locs:
                    existing_locs.add(lk)
                    part["locators"].append(loc)

        # ----------------------------------------------------
        # SEDP Endpoint Discovery Detection (DATA(w) / DATA(r))
        # ----------------------------------------------------
        def extract_sedp_endpoints(node: Any):
            if isinstance(node, dict):
                s_str = json.dumps(node)
                if "rtps.param.topicName" in s_str and ("rtps.param.endpoint_guid" in s_str or "PID_ENDPOINT_GUID" in s_str):
                    cand: Dict[str, Any] = {}

                    def inspect_cand(n: Any):
                        if isinstance(n, dict):
                            for k, v in n.items():
                                if k == "rtps.param.topicName":
                                    cand["topic_name"] = str(v)
                                elif k == "rtps.param.typeName":
                                    cand["type_name"] = str(v)
                                elif k == "rtps.param.endpoint_guid":
                                    guid_full = format_guid(v)
                                    if len(guid_full) >= 24:
                                        cand["endpoint_guid"] = guid_full
                                        kind_hex = guid_full[-2:]
                                        if kind_hex in ("02", "03"):
                                            cand["entity_kind"] = "DataWriter"
                                        elif kind_hex in ("04", "07"):
                                            cand["entity_kind"] = "DataReader"
                                        else:
                                            cand["entity_kind"] = f"Entity (0x{kind_hex})"
                                elif k == "rtps.reliability_kind":
                                    try:
                                        rk_int = int(str(v).split()[0], 0)
                                        cand["reliability"] = RELIABILITY_KINDS.get(rk_int, f"0x{rk_int:x}")
                                    except (ValueError, TypeError):
                                        cand["reliability"] = str(v)
                                elif k == "rtps.durability":
                                    try:
                                        dk_int = int(str(v).split()[0], 0)
                                        cand["durability"] = DURABILITY_KINDS.get(dk_int, f"0x{dk_int:x}")
                                    except (ValueError, TypeError):
                                        cand["durability"] = str(v)
                                elif k == "rtps.ownership":
                                    try:
                                        ok_int = int(str(v).split()[0], 0)
                                        cand["ownership"] = OWNERSHIP_KINDS.get(ok_int, f"0x{ok_int:x}")
                                    except (ValueError, TypeError):
                                        cand["ownership"] = str(v)
                                elif k in ("rtps.history_depth", "rtps.param.history.depth"):
                                    try:
                                        cand["history_depth"] = int(str(v).split()[0], 0)
                                    except (ValueError, TypeError):
                                        pass
                                elif "typeobject" in k.lower() or "type_information" in k.lower() or "pid_type_object" in k.lower():
                                    cand["has_type_object"] = True
                                inspect_cand(v)
                        elif isinstance(n, list):
                            for item in n:
                                inspect_cand(item)

                    inspect_cand(node)
                    if cand.get("topic_name") and cand.get("type_name") and cand.get("endpoint_guid"):
                        ep_guid = cand["endpoint_guid"]
                        if "reliability" not in cand:
                            cand["reliability"] = "BEST_EFFORT"
                        if "durability" not in cand:
                            cand["durability"] = "VOLATILE"
                        if "ownership" not in cand:
                            cand["ownership"] = "SHARED"
                        cand["src_ip"] = src_ip
                        existing = [
                            ep for ep in summary["endpoints"]
                            if ep.get("endpoint_guid") == ep_guid and ep.get("topic_name") == cand["topic_name"]
                        ]
                        if not existing:
                            summary["endpoints"].append(cand)
                        return

                for v in node.values():
                    extract_sedp_endpoints(v)
            elif isinstance(node, list):
                for item in node:
                    extract_sedp_endpoints(item)

        extract_sedp_endpoints(rtps)

    return summary


def generate_junit_report(
    summary: Dict[str, Any],
    output_xml_path: str,
    publisher_name: Optional[str] = None,
    subscriber_name: Optional[str] = None,
    expected_participants: int = 2,
    expected_topic: Optional[str] = None,
    expected_type: Optional[str] = None,
) -> junitparser.JUnitXml:
    """
    Build a comprehensive JUnit XML report evaluating the discovered RTPS topology.
    Writes report to output_xml_path.
    """
    if os.path.exists(output_xml_path):
        try:
            xml = junitparser.JUnitXml.fromfile(output_xml_path)
        except Exception:
            xml = junitparser.JUnitXml()
    else:
        xml = junitparser.JUnitXml()
    suite_title = "rtps_discovery_report"
    if publisher_name and subscriber_name:
        suite_title = f"rtps_discovery_{publisher_name}---{subscriber_name}"
    suite = junitparser.TestSuite(suite_title)

    participants = summary.get("participants", {})
    endpoints = summary.get("endpoints", [])
    part_count = len(participants)

    # ----------------------------------------------------
    # TestCase 1: SPDP Participant Discovery
    # ----------------------------------------------------
    tc_part = junitparser.TestCase("Test_SPDP_Participant_Discovery")
    tc_part.time = 0.1
    part_desc = [f"Discovered {part_count} participant(s):"]
    for guid, p in participants.items():
        loc_str = ", ".join(f"{l['type']}={l['ip']}:{l['port']}" for l in p.get("locators", []))
        part_desc.append(
            f"  - GUID Prefix: {guid}\n"
            f"    Source IP: {p.get('src_ip')}\n"
            f"    Vendor: {p.get('vendor_name')} ({p.get('vendor_id')})\n"
            f"    Protocol Version: {p.get('protocol_version')}\n"
            f"    Lease Duration: {p.get('lease_duration_sec')}s\n"
            f"    Locators: {loc_str or 'none'}"
        )
    tc_part.system_out = "\n".join(part_desc)

    if part_count < expected_participants:
        msg = (
            f"Expected at least {expected_participants} participant(s), "
            f"but found {part_count}."
        )
        failure = junitparser.Failure(msg)
        tc_part.result = [failure]
    suite.add_testcase(tc_part)

    # ----------------------------------------------------
    # TestCase 2: RTPS Protocol Version Compliance
    # ----------------------------------------------------
    tc_ver = junitparser.TestCase("Test_SPDP_Protocol_Version")
    tc_ver.time = 0.05
    ver_issues = []
    ver_lines = []
    for guid, p in participants.items():
        ver_str = str(p.get("protocol_version", "unknown"))
        ver_lines.append(f"Participant {guid[:12]}: RTPS {ver_str}")
        try:
            parts = [int(x) for x in ver_str.split(".")]
            if parts[0] < 2 or (parts[0] == 2 and parts[1] < 1):
                ver_issues.append(f"Participant {guid} has non-standard version RTPS {ver_str}")
        except Exception:
            ver_issues.append(f"Invalid version string '{ver_str}' for participant {guid}")

    tc_ver.system_out = "\n".join(ver_lines)
    if ver_issues:
        tc_ver.result = [junitparser.Failure("; ".join(ver_issues))]
    suite.add_testcase(tc_ver)

    # ----------------------------------------------------
    # TestCase 3: Vendor Identification
    # ----------------------------------------------------
    tc_vendor = junitparser.TestCase("Test_SPDP_Vendor_Identification")
    tc_vendor.time = 0.05
    vendor_lines = []
    for guid, p in participants.items():
        vendor_lines.append(
            f"Participant {guid[:12]}: {p.get('vendor_name')} [ID: {p.get('vendor_id')}]"
        )
    tc_vendor.system_out = "\n".join(vendor_lines)
    suite.add_testcase(tc_vendor)

    # ----------------------------------------------------
    # TestCase 4: Built-in Endpoints Capabilities
    # ----------------------------------------------------
    tc_builtin = junitparser.TestCase("Test_SPDP_Builtin_Endpoints")
    tc_builtin.time = 0.05
    builtin_lines = []
    builtin_issues = []
    for guid, p in participants.items():
        mask = p.get("builtin_endpoints_mask")
        flags = p.get("builtin_endpoints_flags", [])
        builtin_lines.append(
            f"Participant {guid[:12]} Built-in Mask: {mask}\n"
            f"  Flags: {', '.join(flags) if flags else 'None or Default'}"
        )
        if mask == "0x00000000":
            builtin_issues.append(f"Participant {guid} reported empty builtin endpoint set")
    tc_builtin.system_out = "\n".join(builtin_lines)
    if builtin_issues:
        tc_builtin.result = [junitparser.Failure("; ".join(builtin_issues))]
    suite.add_testcase(tc_builtin)

    # ----------------------------------------------------
    # TestCase 5: SEDP Topic & Type Matching
    # ----------------------------------------------------
    tc_sedp = junitparser.TestCase("Test_SEDP_Topic_Type_Match")
    tc_sedp.time = 0.1
    sedp_lines = [f"Discovered {len(endpoints)} endpoint(s):"]
    topics_seen: Set[str] = set()
    types_seen: Set[str] = set()
    writers: List[Dict[str, Any]] = []
    readers: List[Dict[str, Any]] = []

    for ep in endpoints:
        kind = ep.get("entity_kind", "Endpoint")
        topic = ep.get("topic_name", "unknown")
        t_type = ep.get("type_name", "unknown")
        topics_seen.add(topic)
        types_seen.add(t_type)
        if "writer" in kind.lower():
            writers.append(ep)
        elif "reader" in kind.lower():
            readers.append(ep)
        sedp_lines.append(
            f"  - {kind}: Topic='{topic}', Type='{t_type}', GUID={ep.get('endpoint_guid')}\n"
            f"    QoS: Reliability={ep.get('reliability')}, Durability={ep.get('durability')}, Ownership={ep.get('ownership')}"
        )

    tc_sedp.system_out = "\n".join(sedp_lines)

    mismatch_errors = []
    if expected_topic and expected_topic not in topics_seen:
        mismatch_errors.append(f"Expected topic '{expected_topic}' not found in discovery (seen: {topics_seen})")
    if expected_type and expected_type not in types_seen:
        mismatch_errors.append(f"Expected type '{expected_type}' not found in discovery (seen: {types_seen})")

    # If both writers and readers exist, verify topic and type consistency
    if writers and readers:
        w_topics = {w.get("topic_name") for w in writers}
        r_topics = {r.get("topic_name") for r in readers}
        if not (w_topics & r_topics):
            mismatch_errors.append(f"Mismatched topics between Writer(s) {w_topics} and Reader(s) {r_topics}")

        w_types = {w.get("type_name") for w in writers}
        r_types = {r.get("type_name") for r in readers}
        if not (w_types & r_types):
            mismatch_errors.append(f"Mismatched types between Writer(s) {w_types} and Reader(s) {r_types}")

    if mismatch_errors:
        tc_sedp.result = [junitparser.Failure("; ".join(mismatch_errors))]
    suite.add_testcase(tc_sedp)

    # ----------------------------------------------------
    # TestCase 6: SEDP QoS Compatibility
    # ----------------------------------------------------
    tc_qos = junitparser.TestCase("Test_SEDP_QoS_Compatibility")
    tc_qos.time = 0.05
    qos_lines = ["Evaluating QoS profiles between DataWriter and DataReader:"]
    qos_errors = []

    if writers and readers:
        for w in writers:
            for r in readers:
                w_rel = w.get("reliability", "BEST_EFFORT")
                r_rel = r.get("reliability", "BEST_EFFORT")
                w_dur = w.get("durability", "VOLATILE")
                r_dur = r.get("durability", "VOLATILE")

                qos_lines.append(
                    f"Pairing Writer ({w.get('endpoint_guid')}) [{w_rel}, {w_dur}] vs "
                    f"Reader ({r.get('endpoint_guid')}) [{r_rel}, {r_dur}]"
                )

                # Reliability rule: Offered >= Requested (RELIABLE offers to BEST_EFFORT or RELIABLE; BEST_EFFORT cannot offer to RELIABLE)
                if w_rel == "BEST_EFFORT" and r_rel == "RELIABLE":
                    qos_errors.append(
                        f"Incompatible Reliability: Writer is BEST_EFFORT but Reader requested RELIABLE"
                    )

                # Durability rule: Offered >= Requested
                dur_order = {"VOLATILE": 0, "TRANSIENT_LOCAL": 1, "TRANSIENT": 2, "PERSISTENT": 3}
                w_level = dur_order.get(w_dur, 0)
                r_level = dur_order.get(r_dur, 0)
                if w_level < r_level:
                    qos_errors.append(
                        f"Incompatible Durability: Writer offered {w_dur} but Reader requested {r_dur}"
                    )
    else:
        qos_lines.append("Single-sided endpoint or no paired endpoints detected in capture window.")

    tc_qos.system_out = "\n".join(qos_lines)
    if qos_errors:
        tc_qos.result = [junitparser.Failure("; ".join(qos_errors))]
    suite.add_testcase(tc_qos)

    # ----------------------------------------------------
    # TestCase 7: XTypes / TypeInformation
    # ----------------------------------------------------
    tc_xtypes = junitparser.TestCase("Test_SEDP_Type_Information")
    tc_xtypes.time = 0.05
    xtypes_present = any(ep.get("has_type_object") for ep in endpoints)
    tc_xtypes.system_out = (
        f"XTypes TypeInformation/TypeObject detected: {'Yes' if xtypes_present else 'No (Standard CDR)'}"
    )
    suite.add_testcase(tc_xtypes)

    xml.add_testsuite(suite)
    xml.write(output_xml_path)
    return xml


def run_discovery_sniffer(args: argparse.Namespace) -> None:
    """Main execution orchestrator."""
    timestamp = args.timestamp or get_current_timestamp()

    # Determine output XML name
    if args.output:
        output_xml = args.output
    else:
        output_xml = f"junit_discovery_report_{timestamp}.xml"

    # Determine output JSON name
    if args.json_output:
        output_json = args.json_output
    else:
        output_json = f"discovery_report_{timestamp}.json"

    temp_pcap_path = None
    input_pcap = args.pcap

    if not input_pcap:
        # Perform live capture
        if args.write_pcap:
            pcap_file = args.write_pcap
        else:
            fd, temp_pcap_path = tempfile.mkstemp(prefix="rtps_capture_", suffix=".pcap")
            os.close(fd)
            pcap_file = temp_pcap_path

        print(f"[*] Starting live RTPS capture on interface '{args.interface}' for {args.duration}s...")
        captured = capture_traffic_pcap(args.interface, args.duration, pcap_file)
        if not captured:
            print("[-] No UDP/RTPS packets captured during the listening window.")
        input_pcap = pcap_file
    else:
        print(f"[*] Reading existing PCAP file: {input_pcap}")

    raw_packets = dump_rtps_json_from_pcap(input_pcap)
    print(f"[+] Dissected {len(raw_packets)} RTPS packets with tshark.")

    summary = parse_discovery_data(raw_packets)
    summary["metadata"]["interface"] = args.interface
    summary["metadata"]["timestamp"] = timestamp
    if args.publisher:
        summary["metadata"]["publisher"] = args.publisher
    if args.subscriber:
        summary["metadata"]["subscriber"] = args.subscriber

    # Save JSON summary
    to_write: Any = summary
    if os.path.exists(output_json):
        try:
            with open(output_json, "r") as f:
                existing = json.load(f)
            pair_key = (
                f"{args.publisher}---{args.subscriber}"
                if args.publisher and args.subscriber
                else f"run_{timestamp}"
            )
            if isinstance(existing, dict) and "runs" in existing:
                existing["runs"][pair_key] = summary
                to_write = existing
            elif isinstance(existing, dict):
                first_pub = existing.get("metadata", {}).get("publisher", "")
                first_sub = existing.get("metadata", {}).get("subscriber", "")
                first_key = f"{first_pub}---{first_sub}" if (first_pub and first_sub) else "run_1"
                to_write = {
                    "metadata": {"timestamp": timestamp},
                    "runs": {
                        first_key: existing,
                        pair_key: summary,
                    },
                }
        except Exception:
            to_write = summary

    with open(output_json, "w") as f:
        json.dump(to_write, f, indent=2)
    print(f"[+] Discovery JSON summary saved to: {output_json}")

    # Generate JUnit XML Report
    generate_junit_report(
        summary=summary,
        output_xml_path=output_xml,
        publisher_name=args.publisher,
        subscriber_name=args.subscriber,
        expected_participants=args.expected_participants,
        expected_topic=args.expected_topic,
        expected_type=args.expected_type,
    )
    print(f"[+] Discovery JUnit XML report saved to: {output_xml}")

    # Display short summary
    part_count = len(summary["participants"])
    ep_count = len(summary["endpoints"])
    print(f"\n==================== Discovery Summary ====================")
    print(f"Discovered Participants: {part_count}")
    for guid, p in summary["participants"].items():
        print(f"  - [{p.get('vendor_name')}] GUID: {guid} (IP: {p.get('src_ip')}, Ver: {p.get('protocol_version')})")
    print(f"Discovered Endpoints:    {ep_count}")
    for ep in summary["endpoints"]:
        print(f"  - {ep.get('entity_kind')}: Topic='{ep.get('topic_name')}' Type='{ep.get('type_name')}' (QoS: {ep.get('reliability')}, {ep.get('durability')})")
    print(f"===========================================================\n")

    # Cleanup temp pcap if used
    if temp_pcap_path and os.path.exists(temp_pcap_path):
        os.remove(temp_pcap_path)


def main():
    parser = argparse.ArgumentParser(
        description="RTPS Discovery Sniffer & JUnit/JSON Report Generator"
    )
    parser.add_argument(
        "-i",
        "--interface",
        default="any",
        help="Network interface to listen on (e.g. any, lo, eth0). Default: any",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=5,
        help="Capture duration in seconds. Default: 5",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output JUnit XML report file name (default: junit_discovery_report_<timestamp>.xml)",
    )
    parser.add_argument(
        "-j",
        "--json-output",
        default=None,
        help="Output JSON summary file name (default: discovery_report_<timestamp>.json)",
    )
    parser.add_argument(
        "-t",
        "--timestamp",
        default=None,
        help="Explicit timestamp for report naming (matches ./timestamp file format)",
    )
    parser.add_argument(
        "-p",
        "--pcap",
        default=None,
        help="Read and analyze an existing PCAP file instead of live capture",
    )
    parser.add_argument(
        "-w",
        "--write-pcap",
        default=None,
        help="Write live captured packets to specified PCAP file",
    )
    parser.add_argument(
        "-P",
        "--publisher",
        default=None,
        help="Publisher implementation or executable name",
    )
    parser.add_argument(
        "-S",
        "--subscriber",
        default=None,
        help="Subscriber implementation or executable name",
    )
    parser.add_argument(
        "--expected-participants",
        type=int,
        default=2,
        help="Expected number of participants for discovery pass/fail test (default: 2)",
    )
    parser.add_argument(
        "--expected-topic",
        default=None,
        help="Expected topic name to validate (e.g. Square)",
    )
    parser.add_argument(
        "--expected-type",
        default=None,
        help="Expected type name to validate (e.g. ShapeType)",
    )

    args = parser.parse_args()
    run_discovery_sniffer(args)


if __name__ == "__main__":
    main()
