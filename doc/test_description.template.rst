.. include:: vars.rst

.. _section-test-descriptions:

Test Descriptions
=================

Default Values
--------------

This section describes the different test performed. When the test description
mentions 'default settings' or if the test does not mention any QoS modification,
then, it refers to the default values for different QoS settings and other
parameters the ShapeDemo Application configures:

* **Domain ID**: 0
* **RELIABILITY QoS**: reliable
* **DURABILITY QoS**: volatile
* **HISTORY QoS**: default middleware HISTORY kind (should be KEEP_LAST with depth 1)
* **DATA_REPRESENTATION QoS**: XCDR1
* **OWNERSHIP QoS**: shared
* **PARTITION QoS**: default middleware partition
* **DEADLINE QoS**: disabled
* **TIME_BASED_FILTER QoS**: disabled
* **Instance (color value)**: BLUE
* **Topic name**: if not mentioned, the topic used is "Square"
* **Writing period**: 33ms
* **Reading period**: 100ms
* **Delay when creating entities**: at least 1s

The type used in these tests is the following:

.. code-block::

    @appendable
    struct ShapeType {
        @key
        string<128> color;
        int32 x;
        int32 y;
        int32 shapesize;
    };

Additionally, the test description may mention 'Publisher' and 'Subscriber',
this refers to the publisher/subscriber applications. Qos policies are set
to the corresponding entity: DomainParticipant, Publisher, Subscriber, Topic,
DataWriter or DataReader.

Considerations per Product
~~~~~~~~~~~~~~~~~~~~~~~~~~

This section outlines important considerations for different products, including
default values, features enabled or disabled, and unsupported features.

Note that there is no version number because these changes apply to all
product versions.


* **Connext DDS**:

  * Content Filtered Topic expression created with single quotes around strings
    values

* **FastDDS**:

  * Content Filtered Topic expression created with single quotes around strings
    values

* **InterCOM DDS**:

  * Content Filtered Topic expression created with single quotes around strings
    values

* **OpenDDS**:

  * The commands used to build OpenDDS and the test can be found [here](https://github.com/OpenDDS/OpenDDS/blob/master/.github/workflows/dds-rtps.yml). None of the options used affect interoperability. See the [OpenDDS Developer's Guide](https://opendds.readthedocs.io/en/latest-release/devguide/introduction.html#building-and-configuring-for-interoperability) for additional information about interoperability.
  * OpenDDS specific configuration for the test can be found in [shape_configurator_opendds.h](https://github.com/omg-dds/dds-rtps/blob/master/srcCxx/shape_configurator_opendds.h). A brief description is:
    * Use RTPS as the default transport
    * Use RTPS as the default discovery mechanism
    * Disable XTypes Support
  * Content Filtered Topic expression created without single quotes around
    strings values

* **CoreDX DDS**:

  * Content Filtered Topic expression created without single quotes around
    strings values
  * Disabled writer-side content filtering
  * DataReader `send_initial_nack` enabled that sends an initial NACK to every
    discovered DataWriter (only when using reliable RELIABILITY)
  * DataReader `precache_max_samples` set to 0 that sets to 0 the number of
    samples pre-cached (only when using reliable RELIABILITY)
  * Set environment variable `COREDX_UDP_RX_BUFFER_SIZE` to `65536` that
    increases the buffer sizes to that value

* **Dust DDS**:

  *  Content Filtered Topic disabled

|TEST_DESCRIPTION|
