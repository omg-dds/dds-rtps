#################################################################
# Use and redistribution is source and binary forms is permitted
# subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
# at the following URL:
#
# https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
#
#################################################################

from rtps_test_utilities import ReturnCode
import test_suite_functions as tsf

# rtps_test_suite_1 is a dictionary that defines the TestSuite. Each element of
# the dictionary is a Test Case that the interoperability_report.py
# executes.
# The dictionary has the following structure:
#       'name' : {
#           'apps' : [parameter_list],
#           'expected_codes' : [expected_return_code_list],
#           'check_function' : checking_function,
#           'title' : 'This is the title of the test',
#           'description' : 'This is a long description of the test'
#       },
# where:
#       * name: TestCase's name
#       * apps: list in which each element contains the parameters that
#         the shape_main application will use. Each element of the list
#         will run a new app.
#       * expected_codes: list with expected ReturnCodes
#         for a succeed test execution.
#       * check_function [OPTIONAL]: function to check how the subscribers receive
#         the samples from the publishers. By default, it just checks that
#         the data is received. In case that it has a different behavior, that
#         function must be implemented in the test_suite file and the test case
#         should reference it in this parameter.
#       * title: human-readable short description of the test
#       * description: description of the test behavior and parameters
#
# The number of elements in 'apps' list defines how many shape_main
# applications the interoperability_report will run. It should be the same as
# the number of elements in expected_codes.

rtps_test_suite_1 = {
    # DOMAIN
    'Test_Domain_0' : {
        'apps' : ['-P -t Square -d 0', '-S -t Square -d 0 -b'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using Domain ID 0',
        'description' : 'This test covers the most basic interoperability scenario:\n\n'
                        ' * Configures the publisher / subscriber with Domain ID 0\n'
                        ' * Configures the subscriber with BEST_EFFORT reliability\n\n'
                        'The tests passes if the publisher and subscriber discover and match each other and the subscriber '
                            'receives the data from the publisher\n'
    },

    'Test_Domain_1' : {
        'apps' : ['-P -t Square -d 0', '-S -t Square -d 1'],
        'expected_codes' : [ReturnCode.READER_NOT_MATCHED, ReturnCode.DATA_NOT_RECEIVED],
        'title' : 'No communication between publisher and subscriber in a different Domain IDs',
        'description' : 'Verifies that there is no communication between a publisher configured with Domain ID 0 '
                            'and a subscriber configured with Domain ID 1:\n\n'
                        ' * Configures the publisher with Domain ID 0\n'
                        ' * Configures the subscriber with Domain ID 1\n\n'
                        'The tests passes if the publisher and subscriber do not discover each other\n'
    },

    'Test_Domain_2' : {
        'apps' : ['-P -t Square -d 1', '-S -t Square -d 1 -b'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using Domain ID 1',
        'description' : 'This test covers interoperability in a non-default Domain ID:\n\n'
                        ' * Configures the publisher / subscriber with Domain ID 1\n'
                        ' * Configures the subscriber with BEST_EFFORT reliability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The tests passes if the subscriber receives samples from the publisher\n'
    },

    # DATA REPRESENTATION
    'Test_DataRepresentation_0' : {
        'apps' : ['-P -t Square -x 1', '-S -t Square -x 1'],
        'expected_codes' : [ ReturnCode.OK, ReturnCode.OK],
        'title' : 'Default communication using XCDR1',
        'description' : 'This test covers the interoperability scenario with XCDR1:\n\n'
                        ' * Configures the publisher / subscriber with DATA_REPRESENTATION XCDR version 1\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The tests passes if the subscriber receives samples from the publisher\n'
    },

    'Test_DataRepresentation_1' : {
        'apps' : ['-P -t Square -x 1', '-S -t Square -x 2'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Incompatibility publishing XCDR1 and subscribing XCDR2',
        'description' : 'Verifies an XDCR1 publisher does not match with an XCDR2 subscriber and report an '
                            'IncompatibleQos notification\n\n'
                        ' * Configures the publisher with XCDR1 data representation\n'
                        ' * Configures the subscriber with XCDR2 data representation\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_DataRepresentation_2' : {
        'apps' : ['-P -t Square -x 2', '-S -t Square -x 1'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Incompatibility publishing XCDR2 and subscribing XCDR1',
        'description' : 'Verifies an XDCR2 publisher does not match with an XCDR1 subscriber and report an '
                            'IncompatibleQos notification\n\n'
                        ' * Configures the publisher with XCDR2 data representation\n'
                        ' * Configures the subscriber with XCDR1 data representation\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_DataRepresentation_3' : {
        'apps' : ['-P -t Square -x 2', '-S -t Square -x 2 -b'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Default communication using XCDR2',
        'description' : 'This test covers the interoperability scenario with XCDR2:\n\n'
                        ' * Configures publisher / subscriber with DATA_REPRESENTATION XCDR version 2\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The tests passes if the subscriber receives samples from the publisher\n'
    },

    # RELIABILITY
    'Test_Reliability_0' : {
        'apps' : ['-P -t Square -b -z 0', '-S -t Square -b'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_order_w_instances,
        'title' : 'Communication between BEST_EFFORT publisher and subscriber',
        'description' : 'Verifies a best effort publisher communicates with a best effort subscriber with no out-of-order '
                            'or duplicate samples\n\n'
                        ' * Configures the publisher and subscriber with a BEST_EFFORT reliability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the subscriber application receives samples and the value of the "size" member is always increasing\n\n'
                        'The test passes if the value of the "size" is always increasing in '
                            f'{tsf.MAX_SAMPLES_READ} samples read, even if there are missed samples (since reliability '
                            'is BEST_EFFORT) as long as there are no out-of-order or duplicated samples\n'
    },

    'Test_Reliability_1' : {
        'apps' : ['-P -t Square -b', '-S -t Square -r'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'BEST_EFFORT publisher do not match RELIABLE subscribers',
        'description' : 'Verifies a best effort publisher does not match with a reliable subscriber and report an '
                            'IncompatibleQos notification\n\n'
                        ' * Configures the publisher with BEST_EFFORT reliability\n'
                        ' * Configures the publisher with RELIABLE reliability\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Reliability_2' : {
        'apps' : ['-P -t Square -r', '-S -t Square -b'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between RELIABLE publisher and BEST_EFFORT subscriber',
        'description' : 'Verifies a reliable publisher communicates with a best effort subscriber\n\n'
                        ' * Configures the publisher with a RELIABLE reliability\n'
                        ' * Configures the subscriber with a BEST_EFFORT reliability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    # This test only checks that data is received correctly
    'Test_Reliability_3' : {
        'apps' : ['-P -t Square -r', '-S -t Square -r'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using reliability RELIABLE',
        'description' : 'Verifies a reliable publisher communicates with a reliable subscriber\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    # This test checks that data is received in the right order
    'Test_Reliability_4' : {
        'apps' : ['-P -t Square -r -k 0 -z 0', '-S -t Square -r -k 0'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_reliability_no_losses_w_instances,
        'title' : 'Behavior of RELIABLE reliability',
        'description' : 'Verifies a RELIABLE publisher communicates with a RELIABLE subscriber and samples are received '
                            'in order without any losses or duplicates\n\n'
                        ' * Configures the publisher and subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher and subscriber with history KEEP_ALL\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber, after receiving a (first) sample from the publisher, it '
                            f'receives the next {tsf.MAX_SAMPLES_READ} subsequent samples read, without '
                            'losses or duplicates, in the same order as sent\n'
        },

    'Test_Reliability_5' : {
        'apps' : ['-P -t Square -r -k 0 -z 0 --num-instances 4',
                  '-S -t Square -r -k 0'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_reliability_no_losses_w_instances,
        'title' : 'Behavior of RELIABLE reliability with several instances',
        'description' : 'Verifies a RELIABLE publisher using 4 instances communicates with a '
                            'RELIABLE subscriber and samples are received '
                            'in order without any losses or duplicates\n\n'
                        ' * Configures the publisher and subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher and subscriber with history KEEP_ALL\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber, after receiving a (first) sample from the '
                            f'publisher, it receives {tsf.MAX_SAMPLES_READ} subsequent samples per '
                            'instance, without losses or duplicates, in the same order as sent\n'
        },

    'Test_History_0' : {
        'apps' : ['-P -t Square -r -k 5 -z 0 --write-period 50',
                  '-S -t Square -r -k 5 --read-period 200'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_reliability_no_losses_w_instances,
        'title' : 'Behavior of KEEP_LAST history',
        'description' : 'Verifies a RELIABLE, KEEP_LAST 5 publisher using communicates with a '
                            'RELIABLE, KEEP_LAST 5 subscriber and samples are received in order without '
                            'any losses or duplicates. The subscriber reads data 4 time slower than'
                            'the publisher publishes it, but the KEEP_LAST 5 history should be'
                            'enough to avoid losses.\n\n'
                        ' * Configures the publisher and subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher and subscriber with history KEEP_LAST 5\n'
                        ' * Configures the publisher with a writing period of 50ms\n'
                        ' * Configures the subscriber with a reading period of 200ms\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber, after receiving a (first) sample from the '
                            f'publisher, it receives the next {tsf.MAX_SAMPLES_READ} subsequent samples, '
                            'without losses or duplicates, in the same order as sent.\n'
        },

    'Test_History_1' : {
        'apps' : ['-P -t Square -r -k 5 -z 0 --write-period 50 --num-instances 4',
                  '-S -t Square -r -k 5 --read-period 200'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_reliability_no_losses_w_instances,
        'title' : 'Behavior of KEEP_LAST history with several instances',
        'description' : 'Verifies a RELIABLE, KEEP_LAST 5 publisher using 4 instances communicates with a '
                            'RELIABLE, KEEP_LAST 5 subscriber and samples are received in order without '
                            'any losses or duplicates. The subscriber reads data 4 time slower than'
                            'the publisher publishes it, but the KEEP_LAST 5 history should be'
                            'enough to avoid losses.\n\n'
                        ' * Configures the publisher and subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher and subscriber with history KEEP_LAST 5\n'
                        ' * Configures the publisher with a writing period of 50ms\n'
                        ' * Configures the subscriber with a reading period of 200ms\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber, after receiving a (first) sample from the '
                            f'publisher, it receives {tsf.MAX_SAMPLES_READ} subsequent samples per '
                            'instance, without losses or duplicates, in the same order as sent\n'
        },

    # OWNERSHIP
    'Test_Ownership_0' : {
        'apps' : ['-P -t Square -s -1', '-S -t Square -s -1'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between SHARED OWNERSHIP publisher and subscriber',
        'description' : 'Verifies a shared ownership publisher communicates with a shared '
                            'ownership subscriber\n\n'
                        ' * Configures the publisher / subscriber with SHARED ownership\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Ownership_1' : {
        'apps' : ['-P -t Square -s -1', '-S -t Square -s 1'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Incompatibility between SHARED OWNERSHIP publisher and EXCLUSIVE OWNERSHIP subscriber',
        'description' :  'Verifies a shared ownership publisher does not match with an exclusive '
                            'ownership subscriber and report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher with SHARED ownership\n'
                        ' * Configures the subscriber with EXCLUSIVE ownership\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Ownership_2' : {
        'apps' : ['-P -t Square -s 3', '-S -t Square -s -1'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Incompatibility between EXCLUSIVE OWNERSHIP publisher and SHARED OWNERSHIP subscriber',
        'description' : 'Verifies a exclusive ownership publisher does not match with an shared '
                            'ownership subscriber and report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher with EXCLUSIVE ownership\n'
                        ' * Configures the subscriber with SHARED ownership\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    # For Test_Ownership_[3|4|5|6]: each publisher application publishes samples
    # with a different shapesize to allow the subscriber app to recognize from
    # which publisher is receiving the samples.

    # The DataReader should only receive samples from the DataWriter with higher
    # ownership. There may be the situation that the DataReader starts receiving
    # samples from one DataWriter until another DataWriter with higher ownership
    # strength is created. This should be handled by test_size_receivers().
    'Test_Ownership_3': {
        'apps' : [
            '-P -t Square -s 3 -r -k 0 -c BLUE -z 20',
            '-P -t Square -s 4 -r -k 0 -c BLUE -z 30',
            '-S -t Square -s 1 -r -k 0'],
        'expected_codes' :[
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_ONE],
        'check_function' : tsf.test_size_receivers,
        'title' : 'Behavior of EXCLUSIVE OWNERSHIP QoS with publishers of the same instance',
        'description' : 'Verifies an exclusive ownership subscriber receives samples only from '
                            'the highest ownership strength publisher of the same instance\n\n'
                        ' * Use RELIABLE Qos in all publishers and subscriber to avoid samples losses\n'
                        ' * Use KEEP_ALL HISTORY Qos in all publishers and subscriber\n'
                        ' * Configures a first publisher with EXCLUSIVE ownership with strength of 3\n'
                        ' * Configures the first publisher to publish samples with "color" equal to "BLUE" '
                            'and "size" equal to 20\n'
                        ' * Configures a second publisher with EXCLUSIVE ownership and strength of 4\n'
                        ' * Configures the second publisher to publish samples with "color" equal to "BLUE" '
                            ' and "size" equal to 30\n'
                        ' * Configures a subscriber with EXCLUSIVE ownership\n'
                        ' * Verifies that both publishers discover and match the subscriber and vice-versa\n'
                        ' * Note that the subscriber may start receiving samples from the lower ownership strength '
                            'publisher if it is created before the highest strength ownership publisher. This behavior '
                            'is expected and those samples are ignored\n\n'
                        'The test passes if the subscriber receives samples from the highest strength publisher only '
                            '(after receiving the first sample of that publisher. The subscriber reads '
                            f'{tsf.MAX_SAMPLES_READ} samples in total\n'
    },

    # The DataReader should receive from both publisher apps because they
    # publish different instances and the ownership is applied per instance.
    'Test_Ownership_4': {
        'apps' :[
            '-P -t Square -s 3 -r -k 0 -c BLUE -z 20',
            '-P -t Square -s 4 -r -k 0 -c RED -z 30',
            '-S -t Square -s 1 -r -k 0'],
        'expected_codes' : [
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : tsf.test_size_receivers,
        'title' : 'Behavior of EXCLUSIVE OWNERSHIP QoS with publishers with different instances',
        'description' : 'Verifies an exclusive ownership subscriber receives samples from different '
                            'publishers that publish different instances (ShapeType with different color)\n\n'
                        ' * Use RELIABLE Qos in all publishers and subscriber to avoid samples losses\n'
                        ' * Use KEEP_ALL HISTORY Qos in all publishers and subscriber\n'
                        ' * Configures a first publisher with EXCLUSIVE ownership with strength of 3\n'
                        ' * Configures the first publisher to publish samples with "color" equal to "BLUE" '
                            ' and "size" equal to 20\n'
                        ' * Configures a second publisher with EXCLUSIVE ownership and strength of 4\n'
                        ' * Configures the second publisher to publish samples with "color" equal to "RED" '
                            'and "size" equal to 30\n'
                        ' * Configures a subscriber with EXCLUSIVE ownership\n'
                        ' * Verifies that both publishers discover and match the subscriber and vice-versa\n\n'
                        'The test passes if the subscriber receives samples from both publishers in the first '
                            f'{tsf.MAX_SAMPLES_READ} samples\n'
    },

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_5': {
        'apps' : [
            '-P -t Square -s -1 -r -k 0 -c BLUE -z 20',
            '-P -t Square -s -1 -r -k 0 -c BLUE -z 30',
            '-S -t Square -s -1 -r -k 0'],
        'expected_codes' :[
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : tsf.test_size_receivers,
        'title' : 'Behavior of SHARED OWNERSHIP QoS with publishers with the same instance',
        'description' : 'Verifies a shared ownership subscriber receives samples from all '
                            'shared ownership publishers of the different instances\n\n'
                        ' * Use RELIABLE Qos in all publishers and subscriber to avoid samples losses\n'
                        ' * Use KEEP_ALL HISTORY Qos in all publishers and subscriber\n'
                        ' * Configures a first publisher with SHARED ownership\n'
                        ' * Configures the first publisher to publish samples with "color" equal to "BLUE" '
                            'and "size" equal to 20\n'
                        ' * Configures a second publisher with SHARED ownership\n'
                        ' * Configures the second publisher to publish samples with "color" equal to "BLUE" '
                            'and "size" equal to 30\n'
                        ' * Configures a subscriber with SHARED ownership\n'
                        ' * Verifies that both publishers discover and match the subscriber and vice-versa\n\n'
                        'The test passes if the subscriber receives samples from both publishers in the first '
                            f'{tsf.MAX_SAMPLES_READ} samples\n'
    },

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_6': {
        'apps' : [
            '-P -t Square -s -1 -r -k 0 -c BLUE -z 20',
            '-P -t Square -s -1 -r -k 0 -c RED -z 30',
            '-S -t Square -s -1 -r -k 0'],
        'expected_codes' : [
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : tsf.test_size_receivers,
        'title' : 'Behavior of SHARED OWNERSHIP QoS with different instances',
        'description' : 'Verifies a shared ownership subscriber receives samples from all '
                            'shared ownership publishers of different instances\n\n'
                        ' * Use RELIABLE Qos in all publishers and subscriber to avoid samples losses\n'
                        ' * Use KEEP_ALL HISTORY Qos in all publishers and subscriber\n'
                        ' * Configures a first publisher with SHARED ownership with strength of 3\n'
                        ' * Configures the first publisher to publish samples with "color" equal to "BLUE" '
                            'and "size" equal to 20\n'
                        ' * Configures a second publisher with SHARED ownership and strength of 4\n'
                        ' * Configures the second publisher to publish samples with "color" equal to "RED" '
                            'and "size" equal to 30\n'
                        ' * Configures a subscriber with SHARED ownership\n'
                        ' * Verifies that both publishers discover and match the subscriber and vice-versa\n\n'
                        'The test passes if the subscriber receives samples from both publishers in the first '
                            f'{tsf.MAX_SAMPLES_READ} samples\n'
    },

    # DEADLINE
    'Test_Deadline_0' : {
        'apps' : ['-P -t Square -f 3000', '-S -t Square -f 5000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication with publisher deadline smaller than subscriber deadline',
        'description' : 'Verifies there is communication between a publisher with a deadline smaller than the subscriber\n\n'
                        ' * Configures the publisher with DEADLINE of 3 seconds\n'
                        ' * Configures the subscriber with DEADLINE of 5 seconds\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Deadline_1' : {
        'apps' : ['-P -t Square -f 5000', '-S -t Square -f 5000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication with the same publisher and subscriber deadlines',
        'description' : 'Verifies there is communication between a publisher with the same deadline as the subscriber\n\n'
                        ' * Configures the publisher with DEADLINE of 5 seconds\n'
                        ' * Configures the subscriber with DEADLINE of 5 seconds\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Deadline_2' : {
        'apps' : ['-P -t Square -f 7000', '-S -t Square -f 5000'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility with publisher deadline higher than subscriber deadline',
        'description' : 'Verifies there is no communication between a publisher with a higher deadline than the '
                            'subscriber and both report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher with DEADLINE of 7 seconds\n'
                        ' * Configures the publisher with DEADLINE of 5 seconds\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    # This test checks that the deadline is missed in both, publisher and subscriber
    # because the write-period is higher than the deadline period, that means
    # that the samples won't be sent and received on time
    'Test_Deadline_3' : {
        'apps' : ['-P -t Square -f 2000 -w --write-period 3000', '-S -t Square -f 2000'],
        'expected_codes' : [ReturnCode.DEADLINE_MISSED, ReturnCode.DEADLINE_MISSED],
        'check_function' : tsf.test_deadline_missed,
        'title' : 'Deadline is missed in both, publisher and subscriber',
        'description' : 'Verifies that publisher and subscriber miss the deadline\n\n'
                        ' * Configures the publisher with DEADLINE of 2 seconds\n'
                        ' * Configures the subscriber with DEADLINE of 2 seconds\n'
                        ' * Configures the write period to 3 seconds\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the listeners trigger the DeadlineMissed notification in the publisher '
                            'and the subscriber\n'
    },

    # TOPIC
    'Test_Topic_0' : {
        'apps' : ['-P -t Circle', '-S -t Circle'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using the same topic: Circle',
        'description' : 'Verifies communication between a publisher and a subscriber using a specific topic ("Circle")\n\n'
                        ' * Configures the publisher and subscriber to use the topic name "Circle"\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Topic_1' : {
        'apps' : ['-P -t Square', '-S -t Circle'],
        'expected_codes' : [ReturnCode.READER_NOT_MATCHED, ReturnCode.DATA_NOT_RECEIVED],
        'title' : 'No communication when publisher and subscriber are using different topics',
        'description' : 'Verifies that there is no communication between a publisher using topic "Square" '
                            'and a subscriber using topic "Circle"\n\n'
                        ' * Configures the publisher to use the topic name "Square"\n'
                        ' * Configures the subscriber to use the topic name "Circle"\n\n'
                        'The test passes if the publisher and subscriber do not discover each other\n'
    },

    # Content Filtered Topic
    'Test_Cft_0' : {
        'apps' : ['-P -t Square -r -k 0 -c BLUE', '-P -t Square -r -k 0 -c RED', '-S -t Square -r -k 0 -c RED'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK, ReturnCode.RECEIVING_FROM_ONE],
        'check_function' : tsf.test_color_receivers,
        'title' : 'Use of Content filter to avoid receiving undesired data (key)',
        'description' : 'Verifies a subscription using a ContentFilteredTopic does not receive data that does not '
                        'pass the filter. The filter is applied to the key "color"\n\n'
                        ' * Configures a subscriber with a ContentFilteredTopic that selects only the shapes that '
                            'have "color" equal to "RED"\n'
                        ' * Configures a first publisher to publish samples with "color" equal to "BLUE"\n'
                        ' * Configures a second publisher to publish samples with "color" equal to "RED"\n'
                        ' * Use RELIABLE Qos in all publishers and subscriber to ensure any samples that are not '
                            'received are due to filtering\n'
                        ' * Configures the publishers / subscriber with history KEEP_ALL\n'
                        ' * Verifies that both publishers discover and match the subscriber and vice-versa\n'
                        ' * Note that this test does not check whether the filtering happens in the publisher side or '
                            'the subscriber side. It only checks the middleware filters the samples somewhere.\n\n'
                        f'The test passes if the subscriber receives {tsf.MAX_SAMPLES_READ} samples of one color\n'
    },

    'Test_Cft_1': {
        'apps': ['-P -t Square -r -k 0 -z 0 --size-modulo 50', '-S -t Square -r -k 0 --cft "shapesize <= 20"'],
        'expected_codes': [ReturnCode.OK, ReturnCode.OK],
        'check_function': tsf.test_size_less_than_20,
        'title' : 'Use of Content filter to avoid receiving undesired data (non-key)',
        'description': 'Verifies a subscription using a ContentFilteredTopic does not receive data that does not '
                       'pass the filter. The filter is applied to the non-key member "shapesize".\n\n'
                       ' * Use RELIABLE Qos in all publishers and subscriber to avoid samples losses\n'
                       ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                       ' * The publisher application sends samples with increasing value of the "size" member\n'
                       ' * Publisher sends samples with size cycling from 1 to 50 (using --size-modulo 50 and -z 0)\n'
                       ' * Subscriber uses --cft "shapesize <= 20"\n\n'
                       f'The test passes if the subscriber receives {tsf.MAX_SAMPLES_READ/2} samples with size < 20\n'
    },

    # PARTITION
    'Test_Partition_0' : {
        'apps' : ['-P -t Square -p "p1"', '-S -t Square -p "p1"'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between publisher and subscriber using the same partition',
        'description' : 'Verifies communication between a publisher and a subscriber using the same partition\n\n'
                        ' * Configures the publisher and subscriber to use the PARTITION "p1"\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Partition_1' : {
        'apps' : ['-P -t Square -p "p1"', '-S -t Square -p "p2"'],
        'expected_codes' : [ReturnCode.READER_NOT_MATCHED, ReturnCode.DATA_NOT_RECEIVED],
        'title' : 'No communication between publisher and subscriber using different partitions',
        'description' : 'Verifies that there is no communication between a publisher using partition "p1" '
                            'and a subscriber using partition "p2"\n\n'
                        ' * Configures the publisher to use the PARTITION "p1"\n'
                        ' * Configures the subscriber to use the PARTITION "p2"\n\n'
                        'The test passes if the publisher and subscriber do not discover each other\n'
    },

    'Test_Partition_2' : {
        'apps' : ['-P -t Square -p "p1" -c BLUE', '-P -t Square -p "x1" -c RED', '-S -t Square -p "p*"'],
        'check_function' : tsf.test_color_receivers,
        'expected_codes' : [ReturnCode.OK, ReturnCode.READER_NOT_MATCHED, ReturnCode.RECEIVING_FROM_ONE],
        'title' : 'Usage of a partition expression to receive data only from the corresponding publishers',
        'description' : 'Verifies a subscription using a partition expression only receives data from the corresponding '
                            'publishers\n\n'
                        ' * Configures a subscriber with a PARTITION expression "p*" that allows only matching '
                            'publishers whose partition starts with "p"\n'
                        ' * Configures a first publisher to use PARTITION "p1" and "color" equal to "BLUE"\n'
                        ' * Configures a second publisher to use PARTITION "x1" and "color" equal to "RED"\n'
                        ' * Verifies that only the first publisher (PARTITION "p1") discovers and matches subscriber\n'
                        ' * Verifies that the second publisher (PARTITION "x1") does not match the subscriber\n\n'
                        f'The test passes if the subscriber receives {tsf.MAX_SAMPLES_READ} samples of one color '
                        '(first publisher)\n'
    },

    # DURABILITY
    'Test_Durability_0' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between VOLATILE publisher and VOLATILE subscriber',
        'description' : 'Verifies a volatile publisher communicates with a volatile subscriber\n\n'
                        ' * Configures the publisher with a VOLATILE durability\n'
                        ' * Configures the subscriber with a VOLATILE durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_1' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between VOLATILE publisher and TRANSIENT_LOCAL subscriber',
        'description' : 'Verifies a volatile publisher does not match with a transient local subscriber and report an '
                            'IncompatibleQos notification\n\n'
                        ' * Configures the publisher with VOLATILE durability\n'
                        ' * Configures the subscriber with TRANSIENT_LOCAL durability\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Durability_2' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between VOLATILE publisher and TRANSIENT subscriber',
        'description' : 'Verifies a volatile publisher does not match with a transient subscriber and report an '
                            'IncompatibleQos notification\n\n'
                        ' * Configures the publisher with VOLATILE durability\n'
                        ' * Configures the subscriber with TRANSIENT durability\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Durability_3' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between VOLATILE publisher and PERSISTENT subscriber',
        'description' : 'Verifies a volatile publisher does not match with a persistent subscriber and report an '
                            'IncompatibleQos notification\n\n'
                        ' * Configures the publisher with VOLATILE durability\n'
                        ' * Configures the subscriber with PERSISTENT durability\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Durability_4' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT_LOCAL publisher and VOLATILE subscriber',
        'description' : 'Verifies a transient local publisher communicates with a volatile subscriber\n\n'
                        ' * Configures the publisher with a TRANSIENT_LOCAL durability\n'
                        ' * Configures the subscriber with a VOLATILE durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_5' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT_LOCAL publisher and TRANSIENT_LOCAL subscriber',
        'description' : 'Verifies a transient local publisher communicates with a transient local subscriber\n\n'
                        ' * Configures the publisher with a TRANSIENT_LOCAL durability\n'
                        ' * Configures the subscriber with a TRANSIENT_LOCAL durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_6' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between TRANSIENT_LOCAL publisher and TRANSIENT subscriber',
        'description' : 'Verifies a transient local publisher does not match with a transient '
                            'subscriber and report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher with TRANSIENT_LOCAL durability\n'
                        ' * Configures the subscriber with TRANSIENT durability\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Durability_7' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between TRANSIENT_LOCAL publisher and PERSISTENT subscriber',
        'description' : 'Verifies a transient local publisher does not match with a persistent '
                            'subscriber and report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher with TRANSIENT_LOCAL durability\n'
                        ' * Configures the subscriber with PERSISTENT durability\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Durability_8' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT publisher and VOLATILE subscriber',
        'description' : 'Verifies a transient publisher communicates with a volatile subscriber\n\n'
                        ' * Configures the publisher with a TRANSIENT durability\n'
                        ' * Configures the subscriber with a VOLATILE durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_9' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT publisher and TRANSIENT_LOCAL subscriber',
        'description' : 'Verifies a transient publisher communicates with a transient local subscriber\n\n'
                        ' * Configures the publisher with a TRANSIENT durability\n'
                        ' * Configures the subscriber with a TRANSIENT_LOCAL durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_10' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT publisher and TRANSIENT subscriber',
        'description' : 'Verifies a transient publisher communicates with a transient subscriber\n\n'
                        ' * Configures the publisher with a TRANSIENT durability\n'
                        ' * Configures the subscriber with a TRANSIENT durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_11' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between TRANSIENT publisher and PERSISTENT subscriber',
        'description' : 'Verifies a transient publisher does not match with a persistent '
                            'subscriber and report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher with TRANSIENT durability\n'
                        ' * Configures the subscriber with PERSISTENT durability\n\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_Durability_12' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and VOLATILE subscriber',
        'description' : 'Verifies a persistent publisher communicates with a volatile subscriber\n\n'
                        ' * Configures the publisher with a PERSISTENT durability\n'
                        ' * Configures the subscriber with a VOLATILE durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_13' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and TRANSIENT_LOCAL subscriber',
        'description' : 'Verifies a persistent publisher communicates with a transient local subscriber\n\n'
                        ' * Configures the publisher with a PERSISTENT durability\n'
                        ' * Configures the subscriber with a TRANSIENT_LOCAL durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_14' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and TRANSIENT subscriber',
        'description' : 'Verifies a persistent publisher communicates with a transient subscriber\n\n'
                        ' * Configures the publisher with a PERSISTENT durability\n'
                        ' * Configures the subscriber with a TRANSIENT durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Durability_15' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and PERSISTENT subscriber',
        'description' : 'Verifies a persistent publisher communicates with a persistent subscriber\n\n'
                        ' * Configures the publisher with a PERSISTENT durability\n'
                        ' * Configures the subscriber with a PERSISTENT durability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    # Test durability behavior
    # This test sends all samples with reliable reliability and check that the
    # first sample that the subscriber app reads is not the first one
    # (the interoperability_test waits 1 second before creating the second
    # entity, the subscriber, if durability is set)
    'Test_Durability_16' : {
        'apps' : ['-P -t Square -z 0 -r -k 0 -D v -w', '-S -t Square -r -k 0 -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_durability_volatile,
        'title' : 'Test the behavior of the VOLATILE durability',
        'description' : 'Verifies a volatile publisher and subscriber communicates and work as expected\n\n'
                        ' * Configures the publisher / subscriber with a VOLATILE durability\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n'
                        ' * Note that there is at least 1 second delay between the creation of each entity\n\n'
                        'The test passes if the first sample the subscriber receives is not '
                            'the first sample that the publisher sent (by checking the "size" value).\n'
    },

    # This test checks that the subscriber application reads the first sample that
    # have been sent by the publisher before creating the subscriber
    'Test_Durability_17' : {
        'apps' : ['-P -t Square -z 0 -r -k 0 -D l -w', '-S -t Square -r -k 0 -D l'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_durability_transient_local,
        'title' : 'Test the behavior of the TRANSIENT_LOCAL durability',
        'description' : 'Verifies a transient local publisher and subscriber communicates and work as expected\n\n'
                        ' * Configures the publisher / subscriber with a TRANSIENT_LOCAL durability\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n'
                        ' * Note that there is at least 1 second delay between the creation of each entity\n\n'
                        'The test passes if the first sample the subscriber receives is the first sample '
                            'that the publisher sent (by checking the "size" value is equal to 1).\n'
    },

    'Test_TimeBasedFilter_0' : {
        'apps' : ['-P -t Square -r -k 0 -z 0 --write-period 100',
                  '-S -t Square -r -k 0 --time-filter 1000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_reading_1_sample_every_10_samples_w_instances,
        'title' : 'Test the behavior of the TIME_BASED_FILTER QoS',
        'description' : 'Verifies a subscriber with TIME_BASED_FILTER work as expected\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the subscriber TIME_BASED_FILTER to 1 second\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives a sample every 10 samples '
                            'the publisher application has sent. The subscriber has to read '
                            f'{tsf.MAX_SAMPLES_READ/20} samples\n'
    },

    'Test_TimeBasedFilter_1' : {
        'apps' : ['-P -t Square -r -k 0 -z 0 --write-period 100 --num-instances 4',
                  '-S -t Square -r -k 0 --time-filter 1000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_reading_1_sample_every_10_samples_w_instances,
        'title' : 'Test the behavior of the TIME_BASED_FILTER QoS with several instances',
        'description' : 'Verifies a subscriber with TIME_BASED_FILTER work as expected when the publisher '
                            'publishes several instances\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * Configures the subscriber TIME_BASED_FILTER to 1 second\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives a sample every 10 samples '
                            'the publisher application has sent per instance. The subscriber has to read '
                            f'{tsf.MAX_SAMPLES_READ/20} samples per instance\n'
    },

    'Test_FinalInstanceState_0' : {
        'apps' : ['-P -t Square --num-iterations 200 --num-instances 4 --final-instance-state u',
                  '-S -t Square'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_unregistering_w_instances,
        'title' : 'Test the behavior of unregistering instances',
        'description' : 'Verifies a subscriber receives NOT_ALIVE_NO_WRITERS when the publisher unregisters instances\n\n'
                        ' * Configures the publisher to unregister instances upon finalization\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher finishes after running 200 iterations\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives some samples and then '
                            'a NOT_ALIVE_NO_WRITERS per instance\n'
    },

    'Test_FinalInstanceState_1' : {
        'apps' : ['-P -t Square --num-iterations 200 --num-instances 4 --final-instance-state d',
                  '-S -t Square'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_disposing_w_instances,
        'title' : 'Test the behavior of disposing instances',
        'description' : 'Verifies a subscriber receives NOT_ALIVE_DISPOSED when the publisher disposes instances\n\n'
                        ' * Configures the publisher to dispose instances upon finalization\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher finishes after running 200 iterations\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives some samples and then '
                            'a NOT_ALIVE_DISPOSED per instance\n'
    },

    'Test_FinalInstanceState_2' : {
        'apps' : ['-P -t Square --num-iterations 200 --num-instances 4',
                  '-S -t Square'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_unregistering_w_instances,
        'title' : 'Test the instance state when finalizing the application',
        'description' : 'Verifies a subscriber receives NOT_ALIVE_NO_WRITERS when the publisher finishes '
                            'without unregistering or disposing instances explicitly\n\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher finishes after running 200 iterations\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives some samples and then '
                            'a NOT_ALIVE_NO_WRITERS per instance\n'
    },

    'Test_LargeData_0' : {
        'apps' : ['-P -t Square -r -k 0 --additional-payload-size 100000',
                  '-S -t Square -r -k 0'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_large_data,
        'title' : 'Test large data',
        'description' : 'This test covers the interoperability scenario with large data:\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher to use 100000 additional payload size (to represent large data samples)\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The tests passes if the subscriber receives samples from the publisher and '
                            'the last byte sent in additional_payload_size is correctly set.\n'
    },

    'Test_Lifespan_0' : {
        'apps' : ['-P -t Square -r -k 0 -z 0 --write-period 100 --lifespan 250',
                  '-S -t Square -r -k 0 --read-period 500'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan with fractions of seconds, reliable',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan with fractions of seconds\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the publisher with a lifespan of 250ms\n'
                        ' * Configures the subscriber with a reading period of 500ms\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time. The subscriber has to read '
                            f'{tsf.MAX_SAMPLES_READ/10} samples\n'
    },

    'Test_Lifespan_1' : {
        'apps' : ['-P -t Square -r -k 0 -z 0 --write-period 100 --lifespan 250 --num-instances 4',
                  '-S -t Square -r -k 0 --read-period 500'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan with fraction of seconds with several instances, reliable',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan with fraction of seconds and different instances\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the publisher with a lifespan of 250ms\n'
                        ' * Configures the subscriber with a reading period of 500ms\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time per instance. The subscriber has '
                            f'to read {tsf.MAX_SAMPLES_READ/10} samples per instance\n'
    },

    'Test_Lifespan_2' : {
        'apps' : ['-P -t Square -r -k 0 -z 0 --write-period 400 --lifespan 1000',
                  '-S -t Square -r -k 0 --read-period 2000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan expressed in seconds, reliable',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan in seconds\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 400ms\n'
                        ' * Configures the publisher with a lifespan of 1s\n'
                        ' * Configures the subscriber with a reading period of 2s\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time. The subscriber has to read '
                            f'{tsf.MAX_SAMPLES_READ/10} samples per instance\n'
    },

    'Test_Lifespan_3' : {
        'apps' : ['-P -t Square -r -k 0 -z 0 --write-period 400 --lifespan 1000 --num-instances 4',
                  '-S -t Square -r -k 0 --read-period 2000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan expressed in seconds with several instances, reliable',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan in seconds, and different instances\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 400ms\n'
                        ' * Configures the publisher with a lifespan of 1s\n'
                        ' * Configures the subscriber with a reading period of 2s\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time per instance. The subscriber has '
                            f'to read {tsf.MAX_SAMPLES_READ/10} samples per instance\n'
    },

    'Test_Lifespan_4' : {
        'apps' : ['-P -t Square -b -z 0 --write-period 100 --lifespan 250',
                  '-S -t Square -b -k 0 --read-period 500'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan with fractions of seconds, best effort',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan with fractions of seconds\n\n'
                        ' * Configures the publisher / subscriber with a BEST_EFFORT reliability\n'
                        ' * Configures the subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the publisher with a lifespan of 250ms\n'
                        ' * Configures the subscriber with a reading period of 500ms\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time. The subscriber has to read '
                            f'{tsf.MAX_SAMPLES_READ/10} samples\n'
    },

    'Test_Lifespan_5' : {
        'apps' : ['-P -t Square -b -z 0 --write-period 100 --lifespan 250 --num-instances 4',
                  '-S -t Square -b -k 0 --read-period 500'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan with fraction of seconds with several instances, best effort',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan with fraction of seconds and different instances\n\n'
                        ' * Configures the publisher / subscriber with a BEST_EFFORT reliability\n'
                        ' * Configures the subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the publisher with a lifespan of 250ms\n'
                        ' * Configures the subscriber with a reading period of 500ms\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time per instance. The subscriber has '
                            f'to read {tsf.MAX_SAMPLES_READ/10} samples per instance\n'
    },

    'Test_Lifespan_6' : {
        'apps' : ['-P -t Square -b -z 0 --write-period 400 --lifespan 1000',
                  '-S -t Square -b -k 0 --read-period 2000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan expressed in seconds, best effort',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan in seconds\n\n'
                        ' * Configures the publisher / subscriber with a BEST_EFFORT reliability\n'
                        ' * Configures the subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 400ms\n'
                        ' * Configures the publisher with a lifespan of 1s\n'
                        ' * Configures the subscriber with a reading period of 2s\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time. The subscriber has to read '
                            f'{tsf.MAX_SAMPLES_READ/10} samples\n'
    },

    'Test_Lifespan_7' : {
        'apps' : ['-P -t Square -b -z 0 --write-period 400 --lifespan 1000 --num-instances 4',
                  '-S -t Square -b -k 0 --read-period 2000'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.test_lifespan_2_3_consecutive_samples_w_instances,
        'title' : 'Test the behavior of lifespan expressed in seconds with several instances, best effort',
        'description' : 'Verifies a subscriber receives the expected samples when the publisher uses '
                            ' lifespan in seconds, and different instances\n\n'
                        ' * Configures the publisher / subscriber with a BEST_EFFORT reliability\n'
                        ' * Configures the subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher with a writing period of 400ms\n'
                        ' * Configures the publisher with a lifespan of 1s\n'
                        ' * Configures the subscriber with a reading period of 2s\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives 2 or 3 consecutive samples '
                            'each time it reads.\n'
                        'As the publisher sets the lifespan, it expires in some samples before the '
                            'subscriber reads data. The amount of consecutive samples read by the '
                            'subscriber application is 2 or 3 each time per instance. The subscriber has '
                            f'to read {tsf.MAX_SAMPLES_READ/10} samples per instance\n'
    },


    'Test_OrderedAccess_0' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope i',
                  '-S -t Square -r -k 0 --ordered --access-scope i'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for ordered access between INSTANCE_PRESENTATION publisher and '
                    'INSTANCE_PRESENTATION subscriber',
        'description' : 'Verifies an INSTANCE_PRESENTATION publisher is compatible with an '
                            'INSTANCE_PRESENTATION subscriber when using ordered access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with INSTANCE_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with INSTANCE_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_OrderedAccess_1' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope i',
                  '-S -t Square -r -k 0 --ordered --access-scope t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for ordered access between INSTANCE_PRESENTATION publisher and '
                    'TOPIC_PRESENTATION subscriber',
        'description' : 'Verifies an INSTANCE_PRESENTATION publisher does not match with a '
                            'TOPIC_PRESENTATION subscriber when using ordered access and '
                            'report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with INSTANCE_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with TOPIC_PRESENTATION access_scope\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },
    'Test_OrderedAccess_2' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope i',
                  '-S -t Square -r -k 0 --ordered --access-scope g'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for ordered access between INSTANCE_PRESENTATION publisher and '
                    'GROUP_PRESENTATION subscriber',
        'description' : 'Verifies an INSTANCE_PRESENTATION publisher does not match with a '
                            'GROUP_PRESENTATION subscriber when using ordered access and '
                            'report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with INSTANCE_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with GROUP_PRESENTATION access_scope\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },
    'Test_OrderedAccess_3' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope t',
                  '-S -t Square -r -k 0 --ordered --access-scope i'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for ordered access between TOPIC_PRESENTATION publisher and '
                    'INSTANCE_PRESENTATION subscriber',
        'description' : 'Verifies a TOPIC_PRESENTATION publisher compatible with an '
                            'INSTANCE_PRESENTATION subscriber when using ordered access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with TOPIC_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with INSTANCE_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_OrderedAccess_4' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope t',
                  '-S -t Square -r -k 0 --ordered --access-scope t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for ordered access between TOPIC_PRESENTATION publisher and '
                    'TOPIC_PRESENTATION subscriber',
        'description' : 'Verifies a TOPIC_PRESENTATION publisher compatible with a '
                            'TOPIC_PRESENTATION subscriber when using ordered access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with TOPIC_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with TOPIC_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_OrderedAccess_5' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope t',
                  '-S -t Square -r -k 0 --ordered --access-scope g'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for ordered access between TOPIC_PRESENTATION publisher and '
                    'GROUP_PRESENTATION subscriber',
        'description' : 'Verifies an TOPIC_PRESENTATION publisher does not match with a '
                            'GROUP_PRESENTATION subscriber when using ordered access and '
                            'report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with TOPIC_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with GROUP_PRESENTATION access_scope\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },
    'Test_OrderedAccess_6' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope g',
                  '-S -t Square -r -k 0 --ordered --access-scope i'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for ordered access between GROUP_PRESENTATION publisher and '
                    'INSTANCE_PRESENTATION subscriber',
        'description' : 'Verifies a GROUP_PRESENTATION publisher compatible with an '
                            'INSTANCE_PRESENTATION subscriber when using ordered access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with GROUP_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with INSTANCE_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_OrderedAccess_7' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope g',
                  '-S -t Square -r -k 0 --ordered --access-scope t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for ordered access between GROUP_PRESENTATION publisher and '
                    'TOPIC_PRESENTATION subscriber',
        'description' : 'Verifies a GROUP_PRESENTATION publisher compatible with a '
                            'TOPIC_PRESENTATION subscriber when using ordered access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with GROUP_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with TOPIC_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_OrderedAccess_8' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope g',
                  '-S -t Square -r -k 0 --ordered --access-scope g'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for ordered access between GROUP_PRESENTATION publisher and '
                    'GROUP_PRESENTATION subscriber',
        'description' : 'Verifies a GROUP_PRESENTATION publisher compatible with an '
                            'GROUP_PRESENTATION subscriber when using ordered access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with ordered access\n'
                        ' * Configures the publisher with GROUP_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with GROUP_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_OrderedAccess_9' : {
        'apps' : ['-P -t Square -r -k 0 --access-scope t',
                  '-S -t Square -r -k 0 --ordered --access-scope t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for no ordered access publisher and ordered access subscriber',
        'description' : 'Verifies that publisher without ordered access does not match with a '
                            'subscriber with ordered access\n\n'
                        ' * Configures the publisher and the subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher and the subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher and the subscriber with access scope TOPIC_PRESENTATION\n'
                        ' * Configures the subscriber with ordered access\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_OrderedAccess_10' : {
        'apps' : ['-P -t Square -r -k 0 --ordered --access-scope t -z 0 --num-instances 4 --write-period 100',
                  '-S -t Square -r -k 0 --ordered --access-scope i --take-read --read-period 400',
                  '-S -t Square -r -k 0 --ordered --access-scope t --take-read --read-period 400'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.ORDERED_ACCESS_INSTANCE, ReturnCode.ORDERED_ACCESS_TOPIC],
        'check_function' : tsf.ordered_access_w_instances,
        'title' : 'Test the behavior of ordered access',
        'description' : 'Verifies subscribers receives data correctly depending on the ordered '
                            'access: TOPIC_PRESENTATION and INSTANCE_PRESENTATION.\n\n'
                        ' * Configures the publisher and all subscribers with a RELIABLE reliability\n'
                        ' * Configures the publisher and all subscribers with history KEEP_ALL\n'
                        ' * Configures the publisher and all subscribers with ordered access\n'
                        ' * Configures the publisher with access scope TOPIC_PRESENTATION\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the first subscriber with access scope INSTANCE_PRESENTATION\n'
                        ' * Configures the second subscriber with access scope TOPIC_PRESENTATION\n'
                        ' * Configures all subscribers to use take() instead of take_next_instance()\n'
                        ' * Configures all subscribers with a reading period of 400ms\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber applications are receiving the instances '
                            'with the specified ordered access / access scope. For INSTANCE_PRESENTATION, '
                            'all the samples for one instance is presented sequentially. For '
                            'TOPIC_PRESENTATION, the subscriber reads the samples in the same '
                            'order they have been published, independently of the instance they'
                            'belong to (one sample of one instance each time). The subscriber has to read '
                            f'{tsf.MAX_SAMPLES_READ} samples per instance\n'
    },

    'Test_CoherentSets_0' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope i',
                  '-S -t Square -r -k 0 --coherent --access-scope i'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for coherent access between INSTANCE_PRESENTATION publisher and '
                    'INSTANCE_PRESENTATION subscriber',
        'description' : 'Verifies an INSTANCE_PRESENTATION publisher is compatible with an '
                            'INSTANCE_PRESENTATION subscriber when using coherent access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with INSTANCE_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with INSTANCE_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_CoherentSets_1' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope i',
                  '-S -t Square -r -k 0 --coherent --access-scope t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for coherent access between INSTANCE_PRESENTATION publisher and '
                    'TOPIC_PRESENTATION subscriber',
        'description' : 'Verifies an INSTANCE_PRESENTATION publisher does not match with a '
                            'TOPIC_PRESENTATION subscriber when using coherent access and '
                            'report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with INSTANCE_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with TOPIC_PRESENTATION access_scope\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },
    'Test_CoherentSets_2' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope i',
                  '-S -t Square -r -k 0 --coherent --access-scope g'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for coherent access between INSTANCE_PRESENTATION publisher and '
                    'GROUP_PRESENTATION subscriber',
        'description' : 'Verifies an INSTANCE_PRESENTATION publisher does not match with a '
                            'GROUP_PRESENTATION subscriber when using coherent access and '
                            'report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with INSTANCE_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with GROUP_PRESENTATION access_scope\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },
    'Test_CoherentSets_3' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope t',
                  '-S -t Square -r -k 0 --coherent --access-scope i'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for coherent access between TOPIC_PRESENTATION publisher and '
                    'INSTANCE_PRESENTATION subscriber',
        'description' : 'Verifies an TOPIC_PRESENTATION publisher is compatible with an '
                            'INSTANCE_PRESENTATION subscriber when using coherent access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with TOPIC_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with INSTANCE_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_CoherentSets_4' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope t',
                  '-S -t Square -r -k 0 --coherent --access-scope t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for coherent access between TOPIC_PRESENTATION publisher and '
                    'TOPIC_PRESENTATION subscriber',
        'description' : 'Verifies an TOPIC_PRESENTATION publisher is compatible with an '
                            'TOPIC_PRESENTATION subscriber when using coherent access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with TOPIC_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with TOPIC_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_CoherentSets_5' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope t',
                  '-S -t Square -r -k 0 --coherent --access-scope g'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for coherent access between TOPIC_PRESENTATION publisher and '
                    'GROUP_PRESENTATION subscriber',
        'description' : 'Verifies an TOPIC_PRESENTATION publisher does not match with a '
                            'GROUP_PRESENTATION subscriber when using coherent access and '
                            'report an IncompatibleQos notification\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with TOPIC_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with GROUP_PRESENTATION access_scope\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },
    'Test_CoherentSets_6' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope g',
                  '-S -t Square -r -k 0 --coherent --access-scope i'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for coherent access between GROUP_PRESENTATION publisher and '
                    'INSTANCE_PRESENTATION subscriber',
        'description' : 'Verifies an GROUP_PRESENTATION publisher is compatible with an '
                            'INSTANCE_PRESENTATION subscriber when using coherent access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with GROUP_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with INSTANCE_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_CoherentSets_7' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope g',
                  '-S -t Square -r -k 0 --coherent --access-scope t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for coherent access between GROUP_PRESENTATION publisher and '
                    'TOPIC_PRESENTATION subscriber',
        'description' : 'Verifies an GROUP_PRESENTATION publisher is compatible with an '
                            'TOPIC_PRESENTATION subscriber when using coherent access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with GROUP_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with TOPIC_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },
    'Test_CoherentSets_8' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope g',
                  '-S -t Square -r -k 0 --coherent --access-scope g'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Compatibility for coherent access between GROUP_PRESENTATION publisher and '
                    'GROUP_PRESENTATION subscriber',
        'description' : 'Verifies an GROUP_PRESENTATION publisher is compatible with an '
                            'GROUP_PRESENTATION subscriber when using coherent access\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher with GROUP_PRESENTATION access_scope\n'
                        ' * Configures the subscriber with GROUP_PRESENTATION access_scope\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_CoherentSets_9' : {
        'apps' : ['-P -t Square -r -k 0 --access-scope t',
                  '-S -t Square -r -k 0 --coherent --access-scope t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility for no coherent access publisher and coherent access subscriber',
        'description' : 'Verifies that publisher without coherent access does not match with a '
                            'subscriber with coherent access\n\n'
                        ' * Configures the publisher and the subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher and the subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher and the subscriber with access scope TOPIC_PRESENTATION\n'
                        ' * Configures the subscriber with coherent access\n'
                        'The test passes if the listeners trigger the IncompatibleQos notification in the publisher '
                            'and the subscriber\n'
    },

    'Test_CoherentSets_10' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope i --num-topics 3 --num-instances 4 --coherent-sample-count 3 --write-period 100 -z 0',
                  '-S -t Square -r -k 0 --coherent --access-scope i --num-topics 3 --take-read --read-period 100'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.coherent_sets_w_instances,
        'title' : 'Test the behavior of coherent access with INSTANCE_PRESENTATION with several instances',
        'description' : 'Verifies subscribers receives data correctly when using coherent '
                            'access INSTANCE_PRESENTATION.\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher / subscriber with access scope INSTANCE_PRESENTATION\n'
                        ' * Configures the publisher / subscriber to use 3 topics\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher creates coherent sets of 3 consecutive samples each instance\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the subscriber to use take() instead of take_next_instance()\n'
                        ' * Configures the subscriber with a reading period of 100ms\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives all samples of a coherent '
                            'set at the same. This coherent set is created with 36 samples: 3 samples per '
                            'instance, 4 instances and 3 topics. This test checks that the consecutive samples received '
                            'per instance and topic is 3 each time we receive a new coherent set of samples. '
                            f'The subscriber has to read {tsf.MAX_SAMPLES_READ} samples per instance\n'
    },
    'Test_CoherentSets_11' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope t --num-topics 3 --num-instances 4 --coherent-sample-count 3 --write-period 100 -z 0',
                  '-S -t Square -r -k 0 --coherent --access-scope t --num-topics 3 --take-read --read-period 100'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.coherent_sets_w_instances,
        'title' : 'Test the behavior of coherent access with TOPIC_PRESENTATION with several instances',
        'description' : 'Verifies subscribers receives data correctly when using coherent '
                            'access TOPIC_PRESENTATION.\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher / subscriber with access scope TOPIC_PRESENTATION\n'
                        ' * Configures the publisher / subscriber to use 3 topics\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher creates coherent sets of 3 consecutive samples each instance\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the subscriber to use take() instead of take_next_instance()\n'
                        ' * Configures the subscriber with a reading period of 100ms\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives all samples of a coherent '
                            'set at the same. This coherent set is created with 36 samples: 3 samples per '
                            'instance, 4 instances and 3 topics. This test checks that the consecutive samples received '
                            'per instance and topic is 3 each time we receive a new coherent set of samples. '
                            f'The subscriber has to read {tsf.MAX_SAMPLES_READ} samples per instance\n'
    },
    'Test_CoherentSets_12' : {
        'apps' : ['-P -t Square -r -k 0 --coherent --access-scope g --num-topics 3 --num-instances 4 --coherent-sample-count 3 --write-period 100 -z 0',
                  '-S -t Square -r -k 0 --coherent --access-scope g --num-topics 3 --take-read --read-period 100'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : tsf.coherent_sets_w_instances,
        'title' : 'Test the behavior of coherent access with GROUP_PRESENTATION with several instances',
        'description' : 'Verifies subscribers receives data correctly when using coherent '
                            'access GROUP_PRESENTATION.\n\n'
                        ' * Configures the publisher / subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher / subscriber with history KEEP_ALL\n'
                        ' * Configures the publisher / subscriber with coherent access\n'
                        ' * Configures the publisher / subscriber with access scope GROUP_PRESENTATION\n'
                        ' * Configures the publisher / subscriber to use 3 topics\n'
                        ' * The publisher publishes 4 different instances (using the same data value)\n'
                        ' * The publisher creates coherent sets of 3 consecutive samples each instance\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Configures the publisher with a writing period of 100ms\n'
                        ' * Configures the subscriber to use take() instead of take_next_instance()\n'
                        ' * Configures the subscriber with a reading period of 100ms\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber application receives all samples of a coherent '
                            'set at the same. This coherent set is created with 36 samples: 3 samples per '
                            'instance, 4 instances and 3 topics. This test checks that the consecutive samples received '
                            'per instance and topic is 3 each time we receive a new coherent set of samples. '
                            f'The subscriber has to read {tsf.MAX_SAMPLES_READ} samples per instance\n'
    },
}
