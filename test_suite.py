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

# This constant is used to limit the maximum number of samples that tests that
# check the behavior needs to read. For example, checking that the data
# is received in order, or that OWNERSHIP works properly, etc...
MAX_SAMPLES_READ = 500

def test_ownership_receivers(child_sub, samples_sent, last_sample_saved, timeout):

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
                the publishers send. Element 1 of the list is for
                publisher 1, etc.
    last_sample_saved: list of multiprocessing Queues with the last
            sample saved on samples_sent for each Publisher. Element 1 of
            the list is for Publisher 1, etc.
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
                pexpect.TIMEOUT, # index = 1
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

def test_color_receivers(child_sub, samples_sent, last_sample_saved, timeout):

    """
    This function is used by test cases that have two publishers and one
    subscriber. This tests that only one of the color is received by the
    subscriber application because it contains a filter that only allows to
    receive data from one color.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern.
    """
    sub_string = re.search('\w\s+(\w+)\s+[0-9]+ [0-9]+ \[[0-9]+\]',
        child_sub.before + child_sub.after)
    first_sample_color = sub_string.group(1)

    max_samples_received = MAX_SAMPLES_READ
    samples_read = 0

    while sub_string is not None and samples_read < max_samples_received:
        current_sample_color = sub_string.group(1)

        # Check that all received samples have the same color
        if current_sample_color != first_sample_color:
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

def test_reliability_order(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests reliability, it checks whether the subscriber receives
    the samples in order.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
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


def test_reliability_no_losses(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests RELIABLE reliability, it checks whether the subscriber
    receives the samples in order and with no losses.

    child_sub: child program generated with pexpect
    samples_sent: list of multiprocessing Queues with the samples
                the publishers send. Element 1 of the list is for
                publisher 1, etc.
    last_sample_saved: not used
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


def test_durability_volatile(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests the volatile durability, it checks that the sample the
    subscriber receives is not the first one. The publisher application sends
    samples increasing the value of the size, so if the first sample that the
    subscriber app doesn't have the size > 5, the test is correct.

    Note: size > 5 to avoid checking only the first sample, that may be an edge
          case where the DataReader hasn't matched with the DataWriter yet and
          the first samples are not received.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
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

def test_durability_transient_local(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests the TRANSIENT_LOCAL durability, it checks that the
    sample the subscriber receives is the first one. The publisher application
    sends samples increasing the value of the size, so if the first sample that
    the subscriber app does have the size == 1, the test is correct.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
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


def test_deadline_missed(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests whether the subscriber application misses the requested
    deadline or not. This is needed in case the subscriber application receives
    some samples and then missed the requested deadline.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
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
        'apps' : ['-P -t Square -b -z 0', '-S -t Square -b -z 0'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : test_reliability_order,
        'title' : 'Communication between BEST_EFFORT publisher and subscriber',
        'description' : 'Verifies a best effort publisher communicates with a best effort subscriber with no out-of-order '
                            'or duplicate samples\n\n'
                        ' * Configures the publisher and subscriber with a BEST_EFFORT reliability\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n'
                        ' * The publisher application sends samples with increasing value of the "size" member\n'
                        ' * Verifies the subscriber application receives samples and the value of the "size" member is always increasing\n\n'
                        'The test passes if the value of the "size" is always increasing in '
                            f'{MAX_SAMPLES_READ} samples, even if there are missed samples (since reliability '
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
        'apps' : ['-P -t Square -r -k 0 -w', '-S -t Square -r -k 0'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'check_function' : test_reliability_no_losses,
        'title' : 'Behavior of RELIABLE reliability',
        'description' : 'Verifies a RELIABLE publisher communicates with a RELIABLE subscriber and samples are received '
                            'in order without any losses or duplicates\n\n'
                        ' * Configures the publisher and subscriber with a RELIABLE reliability\n'
                        ' * Configures the publisher and subscriber with history KEEP_ALL\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber, after receiving a (first) sample from the publisher, it '
                            f'receives the next {MAX_SAMPLES_READ} subsequent samples, without losses or duplicates, in '
                            'the same order as sent\n'
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
    # strength is created. This should be handled by test_ownership_receivers().
    'Test_Ownership_3': {
        'apps' : [
            '-P -t Square -s 3 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s 4 -r -k 0 -c BLUE -w -z 30',
            '-S -t Square -s 1 -r -k 0'],
        'expected_codes' :[
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_ONE],
        'check_function' : test_ownership_receivers,
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
                            f'{MAX_SAMPLES_READ} samples in total\n'
    },

    # The DataReader should receive from both publisher apps because they
    # publish different instances and the ownership is applied per instance.
    'Test_Ownership_4': {
        'apps' :[
            '-P -t Square -s 3 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s 4 -r -k 0 -c RED -w -z 30',
            '-S -t Square -s 1 -r -k 0'],
        'expected_codes' : [
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : test_ownership_receivers,
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
                            f'{MAX_SAMPLES_READ} samples\n'
    },

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_5': {
        'apps' : [
            '-P -t Square -s -1 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s -1 -r -k 0 -c BLUE -w -z 30',
            '-S -t Square -s -1 -r -k 0'],
        'expected_codes' :[
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : test_ownership_receivers,
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
                            f'{MAX_SAMPLES_READ} samples\n'
    },

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_6': {
        'apps' : [
            '-P -t Square -s -1 -r -k 0 -c BLUE -w -z 20',
            '-P -t Square -s -1 -r -k 0 -c RED -w -z 30',
            '-S -t Square -s -1 -r -k 0'],
        'expected_codes' : [
            ReturnCode.OK,
            ReturnCode.OK,
            ReturnCode.RECEIVING_FROM_BOTH],
        'check_function' : test_ownership_receivers,
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
                            f'{MAX_SAMPLES_READ} samples\n'
    },

    # DEADLINE
    'Test_Deadline_0' : {
        'apps' : ['-P -t Square -f 3', '-S -t Square -f 5'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication with publisher deadline smaller than subscriber deadline',
        'description' : 'Verifies there is communication between a publisher with a deadline smaller than the subscriber\n\n'
                        ' * Configures the publisher with DEADLINE of 3 seconds\n'
                        ' * Configures the subscriber with DEADLINE of 5 seconds\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Deadline_1' : {
        'apps' : ['-P -t Square -f 5', '-S -t Square -f 5'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK],
        'title' : 'Communication with the same publisher and subscriber deadlines',
        'description' : 'Verifies there is communication between a publisher with the same deadline as the subscriber\n\n'
                        ' * Configures the publisher with DEADLINE of 5 seconds\n'
                        ' * Configures the subscriber with DEADLINE of 5 seconds\n'
                        ' * Verifies the publisher and subscriber discover and match each other\n\n'
                        'The test passes if the subscriber receives samples from the publisher\n'
    },

    'Test_Deadline_2' : {
        'apps' : ['-P -t Square -f 7', '-S -t Square -f 5'],
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
        'apps' : ['-P -t Square -f 2 --write-period 3000', '-S -t Square -f 2'],
        'expected_codes' : [ReturnCode.DEADLINE_MISSED, ReturnCode.DEADLINE_MISSED],
        'check_function' : test_deadline_missed,
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

    # COLOR
    'Test_Color_0' : {
        'apps' : ['-P -t Square -r -c BLUE', '-P -t Square -r -c RED', '-S -t Square -r -c RED'],
        'expected_codes' : [ReturnCode.OK, ReturnCode.OK, ReturnCode.RECEIVING_FROM_ONE],
        'check_function' : test_color_receivers,
        'title' : 'Use of Content filter to avoid receiving undesired data',
        'description' : 'Verifies a subscription using a ContentFilteredTopic does not receive data that does not pass the filter\n\n'
                        ' * Configures a subscriber with a ContentFilteredTopic that selects only the shapes that '
                            'have "color" equal to "RED"\n'
                        ' * Configures a first publisher to publish samples with "color" equal to "BLUE"\n'
                        ' * Configures a second publisher to publish samples with "color" equal to "RED"\n'
                        ' * Use RELIABLE Qos in all publishers and subscriber to ensure any samples that are not '
                            'received are due to filtering\n'
                        ' * Verifies that both publishers discover and match the subscriber and vice-versa\n'
                        ' * Note that this test does not check whether the filtering happens in the publisher side or '
                            'the subscriber side. It only checks the middleware filters the samples somewhere.\n\n'
                        f'The test passes if the subscriber receives {MAX_SAMPLES_READ} samples of one color\n'
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
        'check_function' : test_color_receivers,
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
                        f'The test passes if the subscriber receives {MAX_SAMPLES_READ} samples of one color (first publisher)\n'
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
        'check_function' : test_durability_volatile,
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
        'check_function' : test_durability_transient_local,
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

}
