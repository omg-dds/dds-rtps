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

.. code-block:: C

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


|TEST_DESCRIPTION|
