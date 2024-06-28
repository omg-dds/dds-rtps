.. include:: vars.rst

.. _section-introduction:

Introduction
============

The |INTEROPERABILITY_TESTS_CP| is a collection of test cases that validate the
wire protocol interoperability of implementations of the Data Distribution Service®
(DDS) standard. The test suite verifies that different DDS implementations communicate as
expected across a variety of scenarios, including various Quality of Service (QoS)
settings.

The |INTEROPERABILITY_TESTS| are publicly available on this repository:
https://github.com/omg-dds/dds-rtps/

Test Descriptions
-----------------

The test cases are implemented on using an application, called |SHAPE_APP|, that is compiled
against each of the DDS implementations, resulting in a different binary executable for each
DDS implementation.

The |SHAPE_APP| has a set of command-line parameters controlling its behavior (e.g. publish versus subscribe),
the Qos settings (e.g. reliability, durability, ownership), and the use of various other features (e.g. Content Filters).
More information on the the command-line options can be found in this README file:
`Shape Application Parameters Section in README
<https://github.com/omg-dds/dds-rtps/?tab=readme-ov-file#shape-application-parameters>`__.

Each test case is is defined in terms of a specific deployment of the |SHAPE_APP| executables,
the parameters used to run each executable, and the expected test result (return code). The produced return code
depends on the output of the |SHAPE_APP|. More information is available in the
README file's Return Code section:
`Return Code Section in README
<https://github.com/omg-dds/dds-rtps/?tab=readme-ov-file#return-code>`__

A test case minimally runs two instances of the |SHAPE_APP|, one acting as a **Publisher** or a **Subscriber** application.
Some test cases may run additional instances when it is required to exercise a particular behavior.

For example, a specific test case may specify running the binary for Implementation1 with parameters
that configure it to publish data with a certain Qos against the binary for Implementation2 with parameters
that cause it to subscribe data with a different Qos. The expected result may state that all
data published by one application should be received by the other one in the correct order without any duplicates.

A test case *passes* if the communication between the **Publisher** and **Subscriber** application(s)
matches what is expected for that scenario. The "expected" behavior may involve receiving all samples sent,
or specific subsets (e.g. when using content filters or exclusive ownership Qos), it may also involve verifying
that samples are received in specific order, or not received at all (e.g. when the Qos is incompatible). Where needed,
a test case defines a ``check_function`` to parse the output printed by the |SHAPE_APP| and determine
whether the test case *passes* or *fails*.

The test cases included in the |INTEROPERABILITY_TESTS| are defined in a
`test suite <https://github.com/omg-dds/dds-rtps/blob/master/test_suite.py#L332>`__
that is part of this repository.

Test Performed
--------------

The |INTEROPERABILITY_TESTS| runs the test cases using all permutations of DDS implementations as **Publisher** and as **Subscriber**
applications. The products included in the tests are the |SHAPE_APPS| uploaded to the
`latest release of the repository <https://github.com/omg-dds/dds-rtps/releases>`__.