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
* **Topic name**: most of the test specify topic Square
* **Writing period**: 33ms
* **Reading period**: 100ms


|TEST_DESCRIPTION|
