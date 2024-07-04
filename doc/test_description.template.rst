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

* **Connext**:
  * Content Filtered Topic expression created with single quotes around strings
    values
* **FastDDS**:
  * Content Filtered Topic expression created with single quotes around strings
    values
* **InteroCOM DDS**:
  * Content Filtered Topic expression created with single quotes around strings
    values
* **OpenDDS**:
  * Content Filtered Topic expression created without single quotes around
    strings values
  * Disabled XTypes Support
* **CoreDX DDS**:
  * Content Filtered Topic expression created without single quotes around
    strings values
  * Disabled writer-side content filter
  * DataReader send_initial_nack enabled
  * DataReader precache_max_samples set to 0
  * Set environment variable `COREDX_UDP_RX_BUFFER_SIZE` to `65536`


|TEST_DESCRIPTION|
