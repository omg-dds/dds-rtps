.. include:: vars.rst

.. _section-introduction:

Introduction
============

The |INTEROPERABILITY_TESTS_CP| provides a testing framework for different
implementations of the Data Distribution Service® (DDS) standard in terms of
interoperability. This ensures that DDS implementations are tested across a
variety of Quality of Service (QoS) policies and other features among different
products.

The DDS Interoperability Tests are publicly available on this repository:
https://github.com/omg-dds/dds-rtps/

Test Descriptions
-----------------

All these tests are based on an application that allows users to create
different test scenarios by setting various QoS policies and enabling/disabling
DDS features, such as content filtering. This application is called |SHAPE_APP|.
More information about the options of this application is available in the
README file's Shape Application parameters section:
`Shape Application Parameters Section in README
<https://github.com/omg-dds/dds-rtps/?tab=readme-ov-file#shape-application-parameters>`__.

A test suite is composed of a set of test cases, which are run with the
|SHAPE_APP| acting as a **Publisher** or a **Subscriber** application.

A test scenario or test case is determined by the parameters used in the
|SHAPE_APP| and the expected test result (return code). The produced return code
depends on the output of the |SHAPE_APP|. More information is available in the
README file's Return Code section:
`Return Code Section in README
<https://github.com/omg-dds/dds-rtps/?tab=readme-ov-file#return-code>`__.

The different test cases that are currently tested are defined in a
`test suite <https://github.com/omg-dds/dds-rtps/blob/master/test_suite.py#L332>`__
that is part of this repository. By default, a test case is considered as
*passed* if there is communication between the **Publisher** and **Subscriber**
applications. Additionally, some test cases may require additional checks to
ensure that the behavior is correct. Each test case may include a
`checking_function` to do so. These `checking functions` are defined in the test
suite as well and determine whether the test case should be considered as
*passed* or *error* depending on some additional checks.

Test Performed
--------------

The |INTEROPERABILITY_TESTS| run the test suite mentioned above with all
combinations of all DDS implementations as **Publisher** and as **Subscriber**
applications. The products used are the |SHAPE_APPS| uploaded to the
`latest release of the repository <https://github.com/omg-dds/dds-rtps/releases>`__,
including a test of the same product as **Publisher** and as **Subscriber**.
