#################################################################
# Use and redistribution is source and binary forms is permitted
# subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
# at the following URL:
#
# https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
#
#################################################################

from rtps_test_utilities import ReturnCode
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
    list_samples_processed = []
    last_first_sample = ''
    last_second_sample = ''

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

        # Take the last sample published by each publisher from their queues
        # ('last_sample_saved[i]') and save them local variables.
        try:
            last_first_sample = last_sample_saved[0].get(block=False)
        except queue.Empty:
            pass

        try:
            last_second_sample = last_sample_saved[1].get(block=False)
        except queue.Empty:
            pass

        # Determine to which publisher the current sample belong to
        if sub_string.group(0) in list_data_received_second:
            current_sample_from_publisher = 2
        elif sub_string.group(0) in list_data_received_first:
            current_sample_from_publisher = 1
        else:
            # If the sample is not in any queue, break the loop if the
            # the last sample for any publisher has already been processed.
            if last_first_sample in list_samples_processed:
                break
            if last_second_sample in list_samples_processed:
                break
            print(f'Last samples: {last_first_sample}, {last_second_sample}')
            # Otherwise, wait a bit and continue
            time.sleep(0.1)
            continue

        # Keep all samples processed in a single list, so we can check whether
        # the last sample published by any publisher has already been processed
        list_samples_processed.append(sub_string.group(0))

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
