#################################################################
# Use and redistribution is source and binary forms is permitted
# subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
# at the following URL:
#
# https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
#
#################################################################

from rtps_test_utilities import ReturnCode, log_message
import re
import pexpect
import queue
import time

# rtps_test_suite_1 is a dictionary that defines the TestSuite. Each element of
# the dictionary is a Test Case that the interoperability_report.py
# executes.
# The dictionary has the following structure:
#       'name' : {
#           'apps' : [parameter_list],
#           'expected_codes' : [expected_return_code_list],
#           'check_function' : checking_function,
#           'title' : 'This is the description of the test',
#           'description' : ' '
#       },
# where:
#       * name: TestCase's name
#       * apps: list in which each element contains the parameters that
#         the shape_main application will use. Each element of the list
#         will run a new app.
#       * expected_codes: list with expected ReturnCodes
#         for a succeed test execution.
#       * check_function [OPTIONAL]: function to check how the Subscribers receive
#         the samples from the Publishers. By default, it just checks that
#         the data is received. In case that it has a different behavior, that
#         function must be implemented in the test_suite file and the test case
#         should reference it in this parameter.
#       * title: human-readable short description of the test
#       * description: description of the test behavior and parameters
#
# The number of elements in 'apps' list defines how many shape_main
# applications the interoperability_report will run. It should be the same as
# the number of elements in expected_codes.

# This constant is used to limit the maximum number of samples that tests that
# check the behavior needs to read. For example, checking that the data
# is received in order, or that OWNERSHIP works properly, etc...
MAX_SAMPLES_READ = 500

def test_ownership_receivers(child_sub, samples_sent, timeout):

    """
    This function is used by test cases that have two publishers and one subscriber.
    This tests that the Ownership QoS works correctly. In order to do that the
    function checks if the subscriber has received samples from one publisher or
    from both. A subscriber has received from both publishers if there is a sample
    from each publisher interleaved. This is done to make sure the subscriber did
    not started receiving samples from the publisher that was run before, and then
    change to the publisher with the greatest ownership.

    child_sub: child program generated with pexpect
    samples_sent: list of multiprocessing Queues with the samples
                the Publishers send. Element 1 of the list is for
                Publisher 1, etc.
    timeout: time pexpect waits until it matches a pattern.

    This functions assumes that the subscriber has already received samples
    from, at least, one publisher.
    """
    first_sample_received_publisher = 0
    ignore_first_samples = True
    first_received = False
    second_received = False
    list_data_received_second = []
    list_data_received_first = []
    max_samples_received = MAX_SAMPLES_READ
    samples_read = 0

    while(samples_read < max_samples_received):
        # take the topic, color, position and size of the ShapeType.
        # child_sub.before contains x and y, and child_sub.after contains
        # [shapesize]
        # Example: child_sub.before contains 'Square     BLUE       191 152'
        #          child_sub.after contains '[30]'
        sub_string = re.search('[0-9]+ [0-9]+ \[[0-9]+\]',
            child_sub.before + child_sub.after)
        # sub_string contains 'x y [shapesize]', example: '191 152 [30]'

        # takes samples written from both publishers stored in their queues
        # ('samples_sent[i]') and save them in different lists.
        # Try to get all available samples to avoid a race condition that
        # happens when the samples are not in the list but the reader has
        # already read them.
        # waits until <max_wait_time> to stop the execution of the loop and
        # returns the code "RECEIVING_FROM_ONE".
        # list_data_received_[first|second] is a list with the samples sent from
        # its corresponding publisher
        try:
            while True:
                list_data_received_first.append(samples_sent[0].get(
                        block=False))
        except queue.Empty:
            pass

        try:
            while True:
                list_data_received_second.append(samples_sent[1].get(
                        block=False))
        except queue.Empty:
            pass

        # Determine to which publisher the current sample belong to
        if sub_string.group(0) in list_data_received_second:
            current_sample_from_publisher = 2
        elif sub_string.group(0) in list_data_received_first:
            current_sample_from_publisher = 1
        else:
            # If the sample is not in any queue, wait a bit and continue
            time.sleep(0.1)
            continue

        # If the app hit this point, it is because the previous subscriber
        # sample has been already read. Then, we can process the next sample
        # read by the subscriber.
        # Get the next samples the subscriber is receiving
        index = child_sub.expect(
            [
                '\[[0-9]+\]', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            break

        samples_read += 1

        # A potential case is that the reader gets data from one writer and
        # then start receiving from a different writer with a higher
        # ownership. This avoids returning RECEIVING_FROM_BOTH if this is
        # the case.
        # This if is only run once we process the first sample received by the
        # subscriber application
        if first_sample_received_publisher == 0:
            if current_sample_from_publisher == 1:
                first_sample_received_publisher = 1
            elif current_sample_from_publisher == 2:
                first_sample_received_publisher = 2

        # Check if the app still needs to ignore samples
        if ignore_first_samples == True:
            if (first_sample_received_publisher == 1 \
                    and current_sample_from_publisher == 2) \
                or (first_sample_received_publisher == 2 \
                    and current_sample_from_publisher == 1):
                # if receiving samples from a different publisher, then stop
                # ignoring samples
                ignore_first_samples = False
            else:
                # in case that the app only receives samples from one publisher
                # this loop always continues and will return RECEIVING_FROM_ONE
                continue

        if current_sample_from_publisher == 1:
            first_received = True
        else:
            second_received = True
        if second_received == True and first_received == True:
            return ReturnCode.RECEIVING_FROM_BOTH

    print(f'Samples read: {samples_read}')
    return ReturnCode.RECEIVING_FROM_ONE

def test_color_receivers(child_sub, samples_sent, timeout):

    """
    This function is used by test cases that have two publishers and one
    subscriber. This tests that only one of the color is received by the
    subscriber application because it contains a filter that only allows to
    receive data from one color.

    child_sub: child program generated with pexpect
    samples_sent: not used
    timeout: time pexpect waits until it matches a pattern.
    """
    sub_string = re.search('\w\s+(\w+)\s+[0-9]+ [0-9]+ \[[0-9]+\]',
        child_sub.before + child_sub.after)
    last_color = current_color = sub_string.group(1)

    max_samples_received = MAX_SAMPLES_READ
    samples_read = 0

    while sub_string is not None and samples_read < max_samples_received:
        # Check that all received samples have the same color
        if last_color != current_color:
            return ReturnCode.RECEIVING_FROM_BOTH

        index = child_sub.expect(
            [
                '\[[0-9]+\]', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )

        if index == 1:
            break

        samples_read += 1

        sub_string = re.search('\w\s+(\w+)\s+[0-9]+ [0-9]+ \[[0-9]+\]',
            child_sub.before + child_sub.after)

    print(f'Samples read: {samples_read}')
    return ReturnCode.RECEIVING_FROM_ONE

def test_reliability_order(child_sub, samples_sent, timeout):
    """
    This function tests reliability, it checks whether the Subscriber receives
    the samples in order.

    child_sub: child program generated with pexpect
    samples_sent: not used
    timeout: not used
    """

    produced_code = ReturnCode.OK

    # Read the first sample printed by the subscriber
    sub_string = re.search('[0-9]+ [0-9]+ \[([0-9]+)\]',
        child_sub.before + child_sub.after)
    last_size = 0

    max_samples_received = MAX_SAMPLES_READ
    samples_read = 0

    while sub_string is not None and samples_read < max_samples_received:
        current_size = int(sub_string.group(1))
        if (current_size > last_size):
            last_size = current_size
        else:
            produced_code = ReturnCode.DATA_NOT_CORRECT
            break

        # Get the next sample the subscriber is receiving
        index = child_sub.expect(
            [
                '\[[0-9]+\]', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            # no more data to process
            break

        samples_read += 1

        # search the next received sample by the subscriber app
        sub_string = re.search('[0-9]+ [0-9]+ \[([0-9]+)\]',
            child_sub.before + child_sub.after)

    print(f'Samples read: {samples_read}')
    return produced_code


def test_reliability_no_losses(child_sub, samples_sent, timeout):
    """
    This function tests RELIABLE reliability, it checks whether the Subscriber
    receives the samples in order and with no losses.

    child_sub: child program generated with pexpect
    samples_sent: list of multiprocessing Queues with the samples
                the Publishers send. Element 1 of the list is for
                Publisher 1, etc.
    timeout: time pexpect waits until it matches a pattern.
    """

    produced_code = ReturnCode.OK
    processed_samples = 0

    # take the first sample received by the subscriber
    sub_string = re.search('[0-9]+ [0-9]+ \[[0-9]+\]',
            child_sub.before + child_sub.after)

    # This makes sure that at least one sample has been received
    if sub_string.group(0) is None:
        produced_code = ReturnCode.DATA_NOT_RECEIVED

    # Get the sample sent by the DataWriter that matches the first sample
    # received
    pub_sample = ""
    try:
        while pub_sample != sub_string.group(0):
            pub_sample = samples_sent[0].get(block=True, timeout=timeout)
    except:
        # If we don't find a sample in the publisher app that matches the
        # first sample received by the DataReader
        produced_code = ReturnCode.DATA_NOT_CORRECT

    # The first execution we don't need to call samples_sent[0].get() because
    # that takes the first element and remove it from the queue. As we have
    # checked before that the samples are the same, we need to skip that part
    # and get the next received sample
    first_execution = True

    max_samples_received = MAX_SAMPLES_READ
    samples_read = 0

    while sub_string is not None and samples_read < max_samples_received:
        # check that all the samples received by the DataReader are in order
        # and matches the samples sent by the DataWriter
        try:
            if first_execution:
                # do nothing because the first execution should already have
                # a pub_sample so we don't need to get it from the queue
                first_execution = False
            else:
                pub_sample = samples_sent[0].get(block=False)

            if pub_sample != sub_string.group(0):
                produced_code = ReturnCode.DATA_NOT_CORRECT
                break
            processed_samples += 1

        except:
            # at least 2 samples should be received
            if processed_samples <= 1:
                produced_code = ReturnCode.DATA_NOT_CORRECT
            break

        # Get the next sample the subscriber is receiving
        index = child_sub.expect(
            [
                '\[[0-9]+\]', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            # no more data to process
            break
        samples_read += 1
        # search the next received sample by the subscriber app
        sub_string = re.search('[0-9]+ [0-9]+ \[[0-9]+\]',
            child_sub.before + child_sub.after)

    print(f'Samples read: {samples_read}')
    return produced_code


def test_durability_volatile(child_sub, samples_sent, timeout):
    """
    This function tests the volatile durability, it checks that the sample the
    Subscriber receives is not the first one. The Publisher application sends
    samples increasing the value of the size, so if the first sample that the
    Subscriber app doesn't have the size > 5, the test is correct.

    Note: size > 5 to avoid checking only the first sample, that may be an edge
          case where the DataReader hasn't matched with the DataWriter yet and
          the first samples are not received.

    child_sub: child program generated with pexpect
    samples_sent: not used
    timeout: not used
    """

    # Read the first sample, if it has the size > 5, it is using volatile
    # durability correctly
    sub_string = re.search('[0-9]+ [0-9]+ \[([0-9]+)\]',
        child_sub.before + child_sub.after)

    # Check if the element received is not the first 5 samples (aka size >= 5)
    # which should not be the case because the subscriber application waits some
    # seconds after the publisher. Checking 5 samples instead of just one to
    # make sure that there is not the case in which the DataReader hasn't
    # matched with the DataWriter yet and the first samples may not be received.
    # The group(1) contains the matching element for the parameter between
    # brackets in the regular expression. In this case is the size as a string.
    if int(sub_string.group(1)) >= 5:
        produced_code = ReturnCode.OK
    else:
        produced_code = ReturnCode.DATA_NOT_CORRECT

    return produced_code

def test_durability_transient_local(child_sub, samples_sent, timeout):
    """
    This function tests the TRANSIENT_LOCAL durability, it checks that the
    sample the Subscriber receives is the first one. The Publisher application
    sends samples increasing the value of the size, so if the first sample that
    the Subscriber app does have the size == 1, the test is correct.

    child_sub: child program generated with pexpect
    samples_sent: not used
    timeout: not used
    """

    # Read the first sample, if it has the size == 1, it is using transient
    # local durability correctly
    sub_string = re.search('[0-9]+ [0-9]+ \[([0-9]+)\]',
        child_sub.before + child_sub.after)

    # Check if the element is the first one sent (aka size == 1), which should
    # be the case for TRANSIENT_LOCAL durability.
    # The group(1) contains the matching element for the parameter between
    # brackets in the regular expression. In this case is the size as a string.
    if int(sub_string.group(1)) == 1:
        produced_code = ReturnCode.OK
    else:
        produced_code = ReturnCode.DATA_NOT_CORRECT

    return produced_code


def test_deadline_missed(child_sub, samples_sent, timeout):
    """
    This function tests whether the subscriber application misses the requested
    deadline or not. This is needed in case the subscriber application receives
    some samples and then missed the requested deadline.

    child_sub: child program generated with pexpect
    samples_sent: not used
    timeout: time pexpect waits until it matches a pattern
    """

    # At this point, the subscriber app has already received one sample
    # Check deadline requested missed
    index = child_sub.expect([
            'on_requested_deadline_missed()', # index = 0
            pexpect.TIMEOUT # index = 1
        ],
        timeout)
    if index == 0:
        return ReturnCode.DEADLINE_MISSED
    else:
        index = child_sub.expect([
            '\[[0-9]+\]', # index = 0
            pexpect.TIMEOUT # index = 1
        ],
        timeout)
        if index == 0:
            return ReturnCode.OK
        else:
            return ReturnCode.DATA_NOT_RECEIVED


rtps_test_suite_1 = {
    # DATA REPRESENTATION
    'Test_DataRepresentation_0' : {
        'apps' : ['-P -t Square -x 1', '-S -t Square -b -x 1'],
        'expected_codes' : [ ReturnCode.OK, ReturnCode.OK],
        'title' : 'Default communication using XCDR1',
        'description' : 'This test covers the most basic interoperability scenario:\n'
                        ' * Joins the default DDS domain (domain_id=0)\n'
                        ' * Publish / Subscribe a Topic of a simple (structured) data-type using XCDR version 1 serialization\n'
                        ' * Use the default DDS Qos settings: (Reliable Writer, Best-Efforts Reader), Volatile DURABILITY, '
                            'Shared OWNERSHIP, No DEADLINE. default PARTITION, etc.\n'
                        'The tests verifies that the Publisher and Subscriber discover and match each other and the Subscriber '
                            'receives the data written by the Publisher\n'
    },

    'Test_DataRepresentation_1' : {
        'apps' : ['-P -t Square -x 1', '-S -t Square -x 2'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Compatibility publishing XCDR1 and subscribing XCDR2',
        'description' : ' '
    },

    'Test_DataRepresentation_2' : {
        'apps' : ['-P -t Square -x 2', '-S -t Square -x 1'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Compatibility publishing XCDR2 and subscribing XCDR1',
        'description' : ' '
    },

    'Test_DataRepresentation_3' : {
        'apps' : ['-P -t Square -x 2', '-S -t Square -x 2'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Default communication using XCDR2',
        'description' : ' '
    },

    # DOMAIN
    'Test_Domain_0' : {
        'apps' : ['-P -t Square -d 0', '-S -t Square -d 0'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using Domain ID 0',
        'description' : ' '
    },

    'Test_Domain_1' : {
        'apps' : ['-P -t Square -d 0', '-S -t Square -d 1'],
        'expected_codes' : [ReturnCode.READER_NOT_MATCHED, ReturnCode.DATA_NOT_RECEIVED],
        'title' : 'No communication between publisher and subscriber in a different Domain IDs',
        'description' : ' '
    },

    'Test_Domain_2' : {
        'apps' : ['-P -t Square -d 1', '-S -t Square -d 1'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using Domain ID 1',
        'description' : ' '
    },

    # RELIABILITY
    'Test_Reliability_0' : {
        'apps' : ['-P -t Square -b', '-S -t Square -b'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : test_reliability_order,
        'title' : 'Communication between Best Effort writers and Readers',
        'description' : 'Verifies a best-effort publisher communicates with a best-effort subscriber with no out-of-order '
                            'or duplicate samples'
                        ' * All applications use the default DDS domain (domain_id=0)'
                        ' * The applications Publish / Subscribe a Topic of a simple (structured) "ShapeType" data-type '
                            'containing an integer "size" member'
                        ' * Configures the Publisher and Subscriber with a BEST_EFFORT reliability. All other Qos are left as default'
                        ' * Verifies the Publisher and Subscriber discover and match each other'
                        ' * The Publisher application sends samples with increasing value of the "size" member'
                        ' * Verifies the Subscriber application receives samples and the value of the "size" member is always increasing'
                        ' * The test passes even if there are missed sampled (since reliability is BEST_EFFORT) as long as '
                            'there are no out-of-order or duplicated samples'
    },

    'Test_Reliability_1' : {
        'apps' : ['-P -t Square -b', '-S -t Square -r'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'BEST_EFFORT Publishers do not match RELIABLE Subscribers',
        'description' : 'Verifies a best-effort publisher does not match with a reliable subscriber and report an '
                            'IncompatibleQos notification.'
                        ' * All applications use the default DDS domain (domain_id=0)'
                        ' * The applications Publish / Subscribe a Topic of a simple (structured) "ShapeType" data-type.'
                        ' * Configures the Publisher with BEST_EFFORT reliability. All other Qos are left as default'
                        ' * Configures the Publisher with RELIABLE reliability. All other Qos are left as default'
                        ' * Verifies the IncompatibleQos listener is notified both on the Publisher and the Subscriber'
    },

    'Test_Reliability_2' : {
        'apps' : ['-P -t Square -r', '-S -t Square -b'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between RELIABLE publisher and BEST_EFFORT subscriber',
        'description' : ' '
    },

    # This test only checks that data is received correctly
    'Test_Reliability_3' : {
        'apps' : ['-P -t Square -r', '-S -t Square -r'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using reliability RELIABLE',
        'description' : ' '
    },

    # This test checks that data is received in the right order
    'Test_Reliability_4' : {
        'apps' : ['-P -t Square -r -k 0 -w', '-S -t Square -r -k 0'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : test_reliability_no_losses,
        'title' : 'Communication between RELIABLE publishers and subscribers',
        'description' : 'Verifies a RELIABLE publisher communicates with a RELIABLE subscriber and samples are received '
                            'in order without any losses or duplicates'
                        ' * All applications use the default DDS domain (domain_id=0)'
                        ' * The applications Publish / Subscribe a Topic of a simple (structured) "ShapeType" data-type '
                            'containing an integer "size" member'
                        ' * Configures the Publisher and Subscriber with a RELIABLE reliability. All other Qos are left as default'
                        ' * Verifies the Publisher and Subscriber discover and match each other'
                        ' * Verifies that after Subscriber receives a (first) sample from the Publisher, it receives all subsequent '
                            'samples, without losses or duplicates, in the same order as sent'
        },

    # DEADLINE
    'Test_Deadline_0' : {
        'apps' : ['-P -t Square -f 3', '-S -t Square -f 5'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication with publisher deadline smaller than subscriber deadline',
        'description' : ' '
    },

    'Test_Deadline_1' : {
        'apps' : ['-P -t Square -f 5', '-S -t Square -f 5'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication with the same publisher and subscriber deadlines',
        'description' : ' '
    },

    'Test_Deadline_2' : {
        'apps' : ['-P -t Square -f 7', '-S -t Square -f 5'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility with publisher deadline higher than subscriber deadline',
        'description' : ' '
    },

    # This test checks that the deadline is missed in both, publisher and subscriber
    # because the write-period is higher than the deadline period, that means
    # that the samples won't be send and received on time
    'Test_Deadline_3' : {
        'apps' : ['-P -t Square -w -f 2 --write-period 3000', '-S -t Square -f 2'],
        'expected_codes' : [ReturnCode.DEADLINE_MISSED, ReturnCode.DEADLINE_MISSED],
        'check_function' : test_deadline_missed,
        'title' : 'Test that deadline is missed in both, publisher and subscriber',
        'description' : ' '
    },

    # TOPIC
    'Test_Topic_0' : {
        'apps' : ['-P -t Circle', '-S -t Circle'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication using the same topic: Circle',
        'description' : ' '
    },

    'Test_Topic_1' : {
        'apps' : ['-P -t Square', '-S -t Circle'],
        'expected_codes' : [ReturnCode.READER_NOT_MATCHED, ReturnCode.DATA_NOT_RECEIVED],
        'title' : 'No communication when publisher and subscriber are using different topics',
        'description' : ' '
    },

    # COLOR
    'Test_Color_0' : {
        'apps' : ['-P -t Square -c BLUE', '-P -t Square -c RED', '-S -t Square -c RED'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK, ReturnCode.RECEIVING_FROM_ONE],
        'check_function' : test_color_receivers,
        'title' : 'Use of Content filter to avoid receiving undesired data',
        'description' : 'Verifies a subscription using a Content Filtered Topic does not receive date that does not pass the filter'
                        ' * Joins the default DDS domain (domain_id=0)'
                        ' * Publish / Subscribe a Topic of a simple (structured) "ShapeType" data-type. This type '
                            'has a "color" member of type string'
                        ' * Configures a Subscriber with a ContentFilteredTopic that selects only the shapes that '
                            'have "color" equal to "RED"'
                        ' * Configures a first Publisher to publish samples with "color" equal to "BLUE"'
                        ' * Configures a second Publisher to publish samples with "color" equal to "RED"'
                        ' * Use RELIABLE Qos in all Publishers and Subscriber to ensure any samples that are not '
                            'received are due to filtering, other Qos are left as default'
                        ' * Verifies that both Publishers discover and match the Subscriber and vice-versa'
                        ' * Verifies that only the samples with color "RED" are received by the Subscriber'
                        ' * Note that this test does not check whether the filtering happens in the Publisher side or '
                            'the Subscriber side. It only checks the middleware filters the samples somewhere.'
        },

    # PARTITION
    'Test_Partition_0' : {
        'apps' : ['-P -t Square -p "p1"', '-S -t Square -p "p1"'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between publisher and subscriber using the same partition',
        'description' : ' '
    },

    'Test_Partition_1' : {
        'apps' : ['-P -t Square -p "p1"', '-S -t Square -p "p2"'],
        'expected_codes' : [ReturnCode.READER_NOT_MATCHED, ReturnCode.DATA_NOT_RECEIVED],
        'title' : 'No communication between publisher and subscriber using different partitions',
        'description' : ' '
    },

    'Test_Partition_2' : {
        'apps' : ['-P -t Square -p "p1" -c BLUE', '-P -t Square -p "x1" -c RED', '-S -t Square -p "p*"'],
        'check_function' : test_color_receivers,
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK, ReturnCode.RECEIVING_FROM_ONE],
        'title' : 'Communication between publisher and subscriber using a partition expression',
        'description' : ' '
    },

    # DURABILITY
    'Test_Durability_0' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between VOLATILE publisher and VOLATILE subscriber',
        'description' : ' '
    },

    'Test_Durability_1' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between VOLATILE publisher and TRANSIENT_LOCAL subscriber',
        'description' : ' '
    },

    'Test_Durability_2' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between VOLATILE publisher and TRANSIENT subscriber',
        'description' : ' '
    },

    'Test_Durability_3' : {
        'apps' : ['-P -t Square -D v', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between VOLATILE publisher and PERSISTENT subscriber',
        'description' : ' '
    },

    'Test_Durability_4' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT_LOCAL publisher and VOLATILE subscriber',
        'description' : ' '
    },

    'Test_Durability_5' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT_LOCAL publisher and TRANSIENT_LOCAL subscriber',
        'description' : ' '
    },

    'Test_Durability_6' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between TRANSIENT_LOCAL publisher and TRANSIENT subscriber',
        'description' : ' '
    },

    'Test_Durability_7' : {
        'apps' : ['-P -t Square -D l', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between TRANSIENT_LOCAL publisher and PERSISTENT subscriber',
        'description' : ' '
    },

    'Test_Durability_8' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT publisher and VOLATILE subscriber',
        'description' : ' '
    },

    'Test_Durability_9' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT publisher and TRANSIENT_LOCAL subscriber',
        'description' : ' '
    },

    'Test_Durability_10' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between TRANSIENT publisher and TRANSIENT subscriber',
        'description' : ' '
    },

    'Test_Durability_11' : {
        'apps' : ['-P -t Square -D t', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'No compatibility between TRANSIENT publisher and PERSISTENT subscriber',
        'description' : ' '
    },

    'Test_Durability_12' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and VOLATILE subscriber',
        'description' : ' '
    },

    'Test_Durability_13' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D l'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and TRANSIENT_LOCAL subscriber',
        'description' : ' '
    },

    'Test_Durability_14' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and TRANSIENT subscriber',
        'description' : ' '
    },

    'Test_Durability_15' : {
        'apps' : ['-P -t Square -D p', '-S -t Square -D p'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between PERSISTENT publisher and PERSISTENT subscriber',
        'description' : ' '
    },

    # Test durability behavior
    # This test sends all samples with reliable reliability and check that the
    # first sample that the subscriber app reads is not the first one
    # (the interoperability_test waits 1 second before creating the second
    # entity, the subscriber, if durability is set)
    'Test_Durability_16' : {
        'apps' : ['-P -t Square -z 0 -r -k 0 -D v -w', '-S -t Square -r -k 0 -D v'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : test_durability_volatile,
        'title' : 'Test the behavior of the VOLATILE durability. This test checks that the first sample received by the '
                        'subscriber application is not the first one that the publisher application sent.',
        'description' : ' '
    },

    # This test checks that the subscriber application reads the first sample that
    # have been sent by the publisher before creating the subscriber
    'Test_Durability_17' : {
        'apps' : ['-P -t Square -z 0 -r -k 0 -D t -w', '-S -t Square -r -k 0 -D t'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : test_durability_transient_local,
        'title' : 'Test the behavior of the TRANSIENT_LOCAL durability. This test checks that the first sample received by the '
                        'subscriber application is the first one that the publisher application sent.',
        'description' : ' '
    },

    # OWNERSHIP
    'Test_Ownership_0' : {
        'apps' : ['-P -t Square -s -1', '-S -t Square -s -1'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication between SHARED OWNERSHIP publisher and subscriber',
        'description' : ' '
    },

    'Test_Ownership_1' : {
        'apps' : ['-P -t Square -s -1', '-S -t Square -s 1'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Incompatibility between SHARED OWNERSHIP publisher and EXCLUSIVE OWNERSHIP subscriber',
        'description' : ' '
    },

    'Test_Ownership_2' : {
        'apps' : ['-P -t Square -s 3', '-S -t Square -s -1'],
        'expected_codes' : [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS],
        'title' : 'Incompatibility between EXCLUSIVE OWNERSHIP publisher and SHARED OWNERSHIP subscriber',
        'description' : ' '
    },

    # For Test_Ownership_[3|4|5|6]: each publisher application publishes samples
    # with a different shapesize to allow the subscriber app to recognize from
    # which Publisher is receiving the samples.

    # The DataReader should receive from both publisher apps because they
    # publish different instances and the ownership is applied per instance.
    'Test_Ownership_3': {
        'apps' :[
            '-P -t Square -s 3 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s 4 -r -k 0 -c RED -w -z 30',
            '-S -t Square -s 1 -r -k 0'],
        'expected_codes' : [
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : test_ownership_receivers,
        'title' : 'Behavior of EXCLUSIVE OWNERSHIP QoS. This test checks that if there are two publisher applications '
                        'for different instances, the subscriber application receives data from both.',
        'description' : ' '
    },

    # The DataReader should only receive samples from the DataWriter with higher
    # ownership. There may be the situation that the DataReader starts receiving
    # samples from one DataWriter until another DataWriter with higher ownership
    # strength is created. This should be handled by test_ownership_receivers().
    'Test_Ownership_4': {
        'apps' : [
            '-P -t Square -s 3 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s 4 -r -k 0 -c BLUE -w -z 30',
            '-S -t Square -s 1 -r -k 0'],
        'expected_codes' :[
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_ONE],
        'check_function' : test_ownership_receivers,
        'title' : 'Behavior of EXCLUSIVE OWNERSHIP QoS. This test checks that if there are two publisher applications '
                        'for the same instance and different strength, the subscriber application receives data from the '
                        'higher strength ownership publisher application.',
        'description' : ' '
    },

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_5': {
        'apps' : [
            '-P -t Square -s -1 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s -1 -r -k 0 -c RED -w -z 30',
            '-S -t Square -s -1 -r -k 0'],
        'expected_codes' : [
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : test_ownership_receivers,
        'title' : 'Behavior of SHARED OWNERSHIP QoS. This test checks that if there are two publisher applications '
                        'for different instances, the subscriber application receives data from both of them.',
        'description' : ' '
    },

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_6': {
        'apps' : [
            '-P -t Square -s -1 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s -1 -r -k 0 -c BLUE -w -z 30',
            '-S -t Square -s -1 -r -k 0'],
        'expected_codes' :[
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : test_ownership_receivers,
        'title' : 'Behavior of SHARED OWNERSHIP QoS. This test checks that if there are two publisher applications '
                        'for the same instance, the subscriber application receives data from both of them.',
        'description' : ' '
    },
}
