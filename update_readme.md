# Report of Changes: Enhanced Error Diagnostics & Vendor Compatibility Handling

## 1. Executive Summary

This update resolves issues where GitHub Actions interoperability test runs frequently reported generic `ERROR` statuses or produced incorrect test classifications across different DDS implementations. 

The primary goals accomplished are:
1. **Elimination of Bare/Generic `ERROR` Messages**: Replaced all uninformative error logs in `srcCxx/shape_main.cxx` with descriptive, context-rich error messages that explicitly state the DDS vendor name, the QoS policy or feature involved, and the specific failure reason.
2. **Early Vendor-Specific Capability Validation**: Introduced vendor-specific check functions in each `shape_configurator_*.h` header to validate command-line options against each vendor's capabilities prior to DDS entity creation.
3. **Resolution of Feature Incompatibilities & Bugs**:
   - Fixed the eProsima Fast DDS Lifespan calculation bug where duration was truncated to 0.
   - Documented and handled `OrderedAccess` and `CoherentSets` restrictions (unsupported by Fast DDS and OpenDDS in this test configuration).
   - Handled `TimeBasedFilter` restrictions (unsupported on Fast DDS and RTI Connext Micro).
   - Handled `Presentation QoS` access scope restrictions on Kongsberg InterCOM DDS.
   - Fixed RTI Connext Micro command-line parsing to avoid false rejections of `-c <color>`.
4. **Distinction Between Failures and Unsupported Features in Test Runner**:
   - `interoperability_report.py` now distinguishes real test failures (`FAILED`) from features unsupported by a vendor (`UNSUPPORTED`).
   - Unsupported tests now extract and print the concrete reason directly to the console and mark the test case as `junitparser.Skipped` (preventing false GitHub Actions test suite failures while retaining full compatibility with `generate_xlsx_report.py`).

---

## 2. Problem Analysis & Specific Issues Addressed

### Issue 1: `OrderedAccess` and `CoherentSets` Support
- **Problem**: Only RTI Connext DDS, Twin Oaks CoreDX, and Kongsberg InterCOM DDS support presentation ordered access and coherent sets. eProsima Fast DDS and OpenDDS do not support them in this configuration. Previously, attempting to run these tests resulted in generic `READER_NOT_MATCHED` or `SUB_UNSUPPORTED_FEATURE` errors without actionable explanations.
- **Solution**: Centralized capability checks in `shape_configurator_eprosima_fast_dds.h` and `shape_configurator_opendds.h` that reject these options immediately with explicit messages (e.g., `"[eProsima Fast DDS] Presentation QoS Ordered Access is not supported by eProsima Fast DDS in this configuration."`).

### Issue 2: `TimeBasedFilter` QoS
- **Problem**: Fast DDS and RTI Connext Micro do not implement minimum separation sample filtering on DataReaders. On Fast DDS, the subscriber received all samples, leading to `DATA_NOT_CORRECT` or failure during test execution.
- **Solution**: Early validation in `shape_configurator_eprosima_fast_dds.h` and `shape_configurator_rti_connext_micro.h` explicitly rejects `--time-filter` with detailed explanation: `"[eProsima Fast DDS] TimeBasedFilter QoS is not supported: Fast DDS does not implement minimum_separation sample filtering on DataReader."`.

### Issue 3: Fast DDS `Lifespan` QoS Calculation Bug
- **Problem**: In `shape_main.cxx`, Fast DDS lifespan was assigned via:
  ```cpp
  dw_qos.lifespan().duration = Duration_t(options->lifespan_us * 1e-6);
  ```
  Because `Duration_t` expects integer seconds (`int32_t`) and nanoseconds (`uint32_t`), passing `0.25` (for 250 ms) truncated the duration to `0` seconds and `0` nanoseconds. As a result, written samples expired immediately, causing `DATA_NOT_RECEIVED` failures.
- **Solution**: Replaced the specialized constructor call with standard duration decomposition:
  ```cpp
  dw_qos.lifespan FIELD_ACCESSOR.duration.SECONDS_FIELD_NAME = options->lifespan_us / 1000000;
  dw_qos.lifespan FIELD_ACCESSOR.duration.nanosec = (options->lifespan_us % 1000000) * 1000;
  ```
  Since `SECONDS_FIELD_NAME` is defined as `seconds` for Fast DDS and `sec` for RTI/OpenDDS, this correctly configures 0 seconds and 250,000,000 nanoseconds.

### Issue 4: InterCOM DDS Presentation QoS Restrictions
- **Problem**: Kongsberg InterCOM DDS supports `INSTANCE_PRESENTATION_QOS` but does not support `GROUP_PRESENTATION_QOS`, nor does it support coherent access with `TOPIC_PRESENTATION_QOS`.
- **Solution**: Handled and cleanly reported in `shape_configurator_intercom_dds.h` with specific error descriptions.

### Issue 5: RTI Connext Micro Argument Parsing
- **Problem**: In `shape_main.cxx`, checking if `cft_expression != NULL || color != NULL` caused `-c <color>` to be incorrectly rejected on RTI Connext Micro as unsupported, even though only ContentFilteredTopic (`--cft`) is unsupported.
- **Solution**: Fixed lines 494–506 so only `--cft` is rejected.

---

## 3. Detailed List of Changes by File

### `srcCxx/shape_configurator_eprosima_fast_dds.h`
- Added `#define DDS_VENDOR_NAME "eProsima Fast DDS"`.
- Implemented `vendor_check_publisher_options()` and `vendor_check_subscriber_options()`:
  - Rejects `ordered_access_enabled` with specific message.
  - Rejects `coherent_set_enabled` with specific message.
  - Rejects access scopes other than `INSTANCE_PRESENTATION_QOS`.
  - Rejects `timebasedfilter_interval_us > 0` on subscriber.

### `srcCxx/shape_configurator_opendds.h`
- Added `#define DDS_VENDOR_NAME "OpenDDS"`.
- Implemented `vendor_check_publisher_options()` and `vendor_check_subscriber_options()`:
  - Rejects `ordered_access_enabled` and `coherent_set_enabled` in this test configuration.
  - Rejects access scopes other than default `INSTANCE_PRESENTATION_QOS`.

### `srcCxx/shape_configurator_rti_connext_micro.h`
- Added `#define DDS_VENDOR_NAME "RTI Connext Micro"`.
- Implemented `vendor_check_publisher_options()` and `vendor_check_subscriber_options()`:
  - Rejects `ordered_access_enabled`, `coherent_set_enabled`, and non-instance access scopes.
  - Rejects `lifespan_us > 0`.
  - Rejects `TRANSIENT_DURABILITY_QOS` and `PERSISTENT_DURABILITY_QOS`.
  - Rejects `timebasedfilter_interval_us > 0`.
  - Rejects `--cft` (ContentFilteredTopic).

### `srcCxx/shape_configurator_intercom_dds.h`
- Added `#define DDS_VENDOR_NAME "Kongsberg InterCOM DDS"`.
- Implemented `vendor_check_publisher_options()` and `vendor_check_subscriber_options()`:
  - Rejects `GROUP_PRESENTATION_QOS`.
  - Rejects coherent access combined with `TOPIC_PRESENTATION_QOS`.

### `srcCxx/shape_configurator_rti_connext_dds.h` & `srcCxx/shape_configurator_toc_coredx_dds.h`
- Added `#define DDS_VENDOR_NAME "RTI Connext DDS"` and `#define DDS_VENDOR_NAME "Twin Oaks CoreDX"`.
- Implemented `vendor_check_publisher_options()` and `vendor_check_subscriber_options()` returning `true`.

### `srcCxx/shape_main.cxx`
- **Error Diagnostics**:
  - Memory allocations (`topics`, `dws`, `drs`, `previous_handles`) now log `[<DDS_VENDOR_NAME>] Error allocating memory for ... (<N> requested)`.
  - Participant factory, participant, and topic creation logs now report exact topic names, domain IDs, and potential root causes (e.g. missing license or QoS mismatch).
  - DataWriter and DataReader creation failures now log `[<DDS_VENDOR_NAME>] Failed to create datawriter/datareader [<index>] for topic: <name> (check QoS compatibility or resource limits)`.
  - Replaced all unbranded fallback errors with `[<DDS_VENDOR_NAME>] ...`.
- **Validation Integration**:
  - `init_publisher()` and `init_subscriber()` call `vendor_check_publisher_options()` and `vendor_check_subscriber_options()` at startup.
- **Duration Fix**:
  - Unified lifespan duration logic for Fast DDS and other vendors.

### `interoperability_report.py`
- **Output Classification**:
  - Detects if any returned code is `PUB_UNSUPPORTED_FEATURE` or `SUB_UNSUPPORTED_FEATURE`.
  - Extracts the exact failure reason line matching `not supported` from the failing entity's console output.
  - Prints:
    ```
    <Test_Name> : UNSUPPORTED (<Entity>: <Reason>)
    ```
    instead of `ERROR`.
  - When an actual failure occurs, prints:
    ```
    <Test_Name> : FAILED (<Entity>: got <ActualCode>, expected <ExpectedCode>)
    ```
    and extracts any explicit error lines from console output.
- **JUnit Reporting**:
  - Sets `test_case.result = [junitparser.Skipped(message)]` for unsupported tests.
  - Preserves full compatibility with `generate_xlsx_report.py`, which checks `case.result[0].message` for `PUB_UNSUPPORTED_FEATURE` and `SUB_UNSUPPORTED_FEATURE`.

---

## 4. Verification & Validation

1. **Python Compilation & Syntax**:
   - `interoperability_report.py`, `test_suite.py`, and `generate_xlsx_report.py` successfully compiled with Python 3.9 without syntax errors.
2. **Regex & Reason Extraction Tests**:
   - Verified that `re.compile('not supported', re.IGNORECASE)` matches all new vendor messages.
   - Tested extraction logic on mock application console outputs.
3. **JUnit XML & Report Compatibility**:
   - Verified that `junitparser.Skipped` produces XML with `errors="0"`, `failures="0"`, `skipped="1"`.
   - Verified that `generate_xlsx_report.py` correctly detects `PUB_UNSUPPORTED` / `SUB_UNSUPPORTED` / `PUB_SUB_UNSUPPORTED` from the skipped case messages.
