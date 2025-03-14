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

def test_reliability_no_losses_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests RELIABLE reliability, it checks whether the subscriber
    receives the samples in order and with no losses (for several instances)

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern.
    """

    produced_code = ReturnCode.OK

    instance_color = []
    instance_seq_num = []
    first_iteration = []
    samples_read = 0

    while samples_read < MAX_SAMPLES_READ:
        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[([0-9]+)\]',
            child_sub.before + child_sub.after)

        if sub_string is not None:
            # add a new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))
                instance_seq_num.append(int(sub_string.group(2)))
                first_iteration.append(True)

            if sub_string.group(1) in instance_color:
                index = instance_color.index(sub_string.group(1))
                if first_iteration[index]:
                    first_iteration[index] = False
                else:
                    # check that the next sequence number is the next value
                    instance_seq_num[index] += 1
                    if instance_seq_num[index] != int(sub_string.group(2)):
                        produced_code = ReturnCode.DATA_NOT_CORRECT
                        break
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
        if index == 0:
            samples_read += 1

    print(f'Samples read: {samples_read}, instances: {instance_color}')
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

def test_reading_each_10_samples_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests whether the subscriber application receives one sample
    out of 10 (for each instance). For example, first sample received with size
    5, the next one should have size 15, then 25...

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    produced_code = ReturnCode.OK

    instance_color = []
    instance_seq_num = []
    first_iteration = []
    max_samples_received = MAX_SAMPLES_READ / 20 # 25
    samples_read = 0

    while samples_read < max_samples_received:

        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[([0-9]+)\]',
            child_sub.before + child_sub.after)

        if sub_string is not None:
            # add a new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))
                instance_seq_num.append(int(sub_string.group(2)))
                first_iteration.append(True)

            if sub_string.group(1) in instance_color:
                index = instance_color.index(sub_string.group(1))
                if first_iteration[index]:
                    first_iteration[index] = False
                else:
                    # check that the received sample has the sequence number
                    # previous + 10
                    if instance_seq_num[index] + 10 != int(sub_string.group(2)):
                        produced_code = ReturnCode.DATA_NOT_CORRECT
                        break
                    instance_seq_num[index] = int(sub_string.group(2))
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
        if index == 0:
            samples_read += 1

    print(f'Samples read: {samples_read}, instances: {instance_color}')
    return produced_code

def test_unregistering_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests whether instances are correctly unregistered

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    produced_code = ReturnCode.OK

    instance_color = []
    unregistered_instance_color = []

    while True:
        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[([0-9]+)\]',
            child_sub.before + child_sub.after)

        if sub_string is not None:
            # add a new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))
        else:
            # if no sample is received, it might be a UNREGISTER message
            sub_string = re.search(r'\w+\s+(\w+)\s+NOT_ALIVE_NO_WRITERS_INSTANCE_STATE',
                child_sub.before + child_sub.after)
            if sub_string is not None:
                unregistered_instance_color.append(sub_string.group(1))
                if len(instance_color) == len(unregistered_instance_color):
                    break
        # Get the next sample the subscriber is receiving or unregister/dispose
        index = child_sub.expect(
            [
                r'\w+\s+\w+\s+.*?\n', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            # no more data to process
            break

    # compare that arrays contain the same elements
    if set(instance_color) == set(unregistered_instance_color):
        produced_code = ReturnCode.OK
    else:
        produced_code = ReturnCode.DATA_NOT_CORRECT

    print(f'Unregistered {len(unregistered_instance_color)} elements: {unregistered_instance_color}')

    return produced_code

def test_disposing_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests whether instances are correctly disposed

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    produced_code = ReturnCode.OK

    instance_color = []
    disposed_instance_color = []

    while True:
        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[([0-9]+)\]',
            child_sub.before + child_sub.after)

        if sub_string is not None:
            # add a new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))
        else:
            # if no sample is received, it might be a DISPOSED message
            sub_string = re.search(r'\w+\s+(\w+)\s+NOT_ALIVE_DISPOSED_INSTANCE_STATE',
                child_sub.before + child_sub.after)
            if sub_string is not None:
                disposed_instance_color.append(sub_string.group(1))
                if len(instance_color) == len(disposed_instance_color):
                    break
        # Get the next sample the subscriber is receiving or unregister/dispose
        index = child_sub.expect(
            [
                r'\w+\s+\w+\s+.*?\n', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            # no more data to process
            break

    # compare that arrays contain the same elements
    if set(instance_color) == set(disposed_instance_color):
        produced_code = ReturnCode.OK
    else:
        produced_code = ReturnCode.DATA_NOT_CORRECT

    print(f'Disposed {len(disposed_instance_color)} elements: {disposed_instance_color}')

    return produced_code

def test_large_data(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests whether large data is correctly received

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    produced_code = ReturnCode.DATA_NOT_CORRECT
    # As the interoperability_test is just looking for the size [<size>],
    # this does not count the data after it, we need to read one more full
    # sample
    index = child_sub.expect(
        [
            r'\w+\s+\w+\s+[0-9]+\s+[0-9]+\s+\[[0-9]+\]\s+\{[0-9]+\}', # index = 0
            pexpect.TIMEOUT # index = 1
        ],
        timeout
    )

    if index == 0:
        # Read the sample received, if it prints the additional_bytes == 255,
        # it is sending large data correctly
        sub_string = re.search(r'\w+\s+\w+\s+[0-9]+\s+[0-9]+\s+\[[0-9]+\]\s+\{([0-9]+)\}',
            child_sub.before + child_sub.after)
        # Check if the last element of the additional_bytes field element is
        # received correctly
        if sub_string is not None:
            if int(sub_string.group(1)) == 255:
                produced_code = ReturnCode.OK
            else:
                produced_code = ReturnCode.DATA_NOT_CORRECT

    return produced_code

def test_lifespan_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests that lifespan works correctly. In the test situation,
    only 2 or 3 consecutive samples should be received each time the reader
    reads data.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    produced_code = ReturnCode.OK

    # as the test is reading in a slower rate, reduce the number of samples read
    max_samples_lifespan = MAX_SAMPLES_READ / 10 # 50

    instance_color = []
    previous_seq_num = []
    first_iteration = []
    samples_read = 0
    consecutive_samples = []

    while samples_read < max_samples_lifespan:
        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[([0-9]+)\]',
            child_sub.before + child_sub.after)

        if sub_string is not None:
            # add a new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))
                previous_seq_num.append(int(sub_string.group(2)))
                first_iteration.append(True)
                consecutive_samples.append(1) # take into account the first sample

            # if the instance exists
            if sub_string.group(1) in instance_color:
                index = instance_color.index(sub_string.group(1))
                # we should receive only 2 or 3 consecutive samples with the
                # parameters defined by the test
                if first_iteration[index]:
                    # do nothing for the first sample received
                    first_iteration[index] = False
                else:
                    # if the sequence number is consecutive, increase the counter
                    if previous_seq_num[index] + 1 == int(sub_string.group(2)):
                        consecutive_samples[index] += 1
                    else:
                        # if the sequence number is not consecutive, check that we
                        # receive only 3 or 2 samples
                        if consecutive_samples[index] == 3 or consecutive_samples[index] == 2:
                            # reset value to 1, as this test consider that the first
                            # sample is consecutive with itself
                            consecutive_samples[index] = 1
                        else:
                            # if the amount of samples received is different than 3 or 2
                            # this is an error
                            produced_code = ReturnCode.DATA_NOT_CORRECT
                            break
                    previous_seq_num[index] = int(sub_string.group(2))

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
        if index == 0:
            samples_read += 1

    print(f'Samples read: {samples_read}, instances: {instance_color}')
    return produced_code

def ordered_access_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests that ordered access works correctly. This counts the
    samples received in order and detects wether they are from the same instance
    as the previously received sample or not.
    If the number of consecutive samples from the same instance is greater than
    the number of consecutive samples form different instances, this means that
    the DW is using INSTANCE_PRESENTATION, if the case is the opposite, it is
    using TOPIC_PRESENTATION.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    produced_code = ReturnCode.OK

    instance_color = []
    samples_read = 0
    previous_sample_color = None
    color_different_count = 0
    color_equal_count = 0
    samples_printed = False

    while samples_read < MAX_SAMPLES_READ:
        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[[0-9]+\]',
            child_sub.before + child_sub.after)

        # if a sample is read
        if sub_string is not None:
            # samples have been printed at least once
            samples_printed = True
            # add new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))

            # the instance exists
            if sub_string.group(1) in instance_color:
                index = instance_color.index(sub_string.group(1))
                current_color = sub_string.group(1)
                # check the previous color and increase the different or equal
                # counters
                if previous_sample_color is not None:
                    if current_color != previous_sample_color:
                        color_different_count += 1
                    else:
                        color_equal_count += 1
                previous_sample_color = current_color
        # different message than a sample
        else:
            sub_string = re.search(r'Reading with ordered access',
                child_sub.before + child_sub.after)
            # if 'Reading with ordered access' message, it means that the DataReader
            # is reading a new set of data (DataReader reads data slower that a
            # DataWriter writes it)
            if sub_string is not None:
                # if samples have been already received by the DataReader and the
                # counter addition (samples read) is greater than 5. It is 5 because
                # there are 4 instances and we need to make sure that we receive
                # at least 1 sample for every instance
                # Note: color_equal_count + color_different_count will be the samples read
                if samples_printed and color_equal_count + color_different_count > 5:
                    # if produced_code is not OK (this will happen in all iterations
                    # except for the first one). We check that the behavior is the same
                    # as in previous iterations.
                    if produced_code != ReturnCode.OK:
                        current_behavior = None
                        if color_equal_count > color_different_count:
                            current_behavior = ReturnCode.ORDERED_ACCESS_INSTANCE
                        elif color_equal_count < color_different_count:
                            current_behavior = ReturnCode.ORDERED_ACCESS_TOPIC
                        # in case of a behavior change, this will be an error
                        if produced_code != current_behavior:
                            produced_code = ReturnCode.DATA_NOT_CORRECT
                            break
                    # this only happens on the first iteration and then this sets
                    # the initial ReturnCode
                    else:
                        if color_equal_count > color_different_count:
                            produced_code = ReturnCode.ORDERED_ACCESS_INSTANCE
                        elif color_equal_count < color_different_count:
                            produced_code = ReturnCode.ORDERED_ACCESS_TOPIC
                # reset counters for the next set of samples read
                color_equal_count = 0
                color_different_count = 0

        # Get the next sample the subscriber is receiving or the next
        # 'Reading with ordered access message'
        index = child_sub.expect(
            [
                r'(Reading with ordered access.*?\n|[\[[0-9]+\])', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            # no more data to process
            break
        if index == 0:
            samples_read += 1

    print(f'Samples read: {samples_read}, instances: {instance_color}')
    return produced_code

def coherent_sets_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests that coherent sets works correctly. This counts the
    consecutive samples received from the same instance. The value should be 3
    as this is the coherent set count that the test is setting.
    Note: when using GROUP_PRESENTATION, the first iteration may print more
    samples (more coherent sets), the test check that the samples received per
    instance is a multiple of 3, so the coherent sets are received complete.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    produced_code = ReturnCode.OK

    topics = {}
    samples_read = 0
    previous_sample_color = None
    new_coherent_set_read = False
    first_time_reading = True

    while samples_read < MAX_SAMPLES_READ:
        sub_string = re.search(r'(\w+)\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[[0-9]+\]',
            child_sub.before + child_sub.after)

        # if a sample is read
        if sub_string is not None:
            # DataReader has received a new coherent set
            new_coherent_set_read = True
            # add new instances to the corresponding topic
            topic_name = sub_string.group(1)
            instance_color = sub_string.group(2)

            if topic_name not in topics:
                topics[topic_name] = {}
            if instance_color not in topics[topic_name]:
                topics[topic_name][instance_color] = 1
            # if the instance is already added
            if instance_color in topics[topic_name]:
                # the instance exists
                current_color = instance_color
                # check the previous color and increase consecutive samples
                if previous_sample_color is not None:
                    if current_color == previous_sample_color:
                        topics[topic_name][instance_color] += 1
                previous_sample_color = current_color
        # different message than a sample
        else:
            sub_string = re.search(r'Reading coherent sets',
                child_sub.before + child_sub.after)
            # if 'Reading coherent sets' message, it means that the DataReader
            # is trying to read a new coherent set, it might not read any sample
            if sub_string is not None:
                # if DataReader has received samples
                if new_coherent_set_read:
                    for topic in topics:
                        for color in topics[topic]:
                            if first_time_reading:
                                # with group presentation we may get several coherent
                                # sets at the beginning, just checking that the samples
                                # received are multiple of 3
                                if topics[topic][color] % 3 != 0:
                                    produced_code = ReturnCode.DATA_NOT_CORRECT
                                    break
                            else:
                                # there should be 3 consecutive samples per instance,
                                # as the test specifies this with the argument
                                # --coherent-sample-count 3
                                if topics[topic][color] != 3:
                                    produced_code = ReturnCode.DATA_NOT_CORRECT
                                    break
                            topics[topic][color] = 1
                    if produced_code == ReturnCode.DATA_NOT_CORRECT:
                        break
                    new_coherent_set_read = False
                    first_time_reading = False

        # Get the next sample the subscriber is receiving or the next
        # 'Reading with ordered access message'
        index = child_sub.expect(
            [
                r'(Reading coherent sets.*?\n|[\[[0-9]+\])', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            # no more data to process
            break
        if index == 0:
            samples_read += 1

    print(f'Samples read: {samples_read}')
    print("Instances:")
    for topic in topics:
        print(f"Topic {topic}: {', '.join(topics[topic].keys())}")

    return produced_code
