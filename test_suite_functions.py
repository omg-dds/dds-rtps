#################################################################
# Use and redistribution is source and binary forms is permitted
# subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
# at the following URL:
#
# https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
#
#################################################################

from rtps_test_utilities import ReturnCode, basic_check
import re
import pexpect
import queue
import time

# This constant is used to limit the maximum number of samples that tests that
# check the behavior needs to read. For example, checking that the data
# is received in order, or that OWNERSHIP works properly, etc...
MAX_SAMPLES_READ = 500

def test_size_receivers(child_sub, samples_sent, last_sample_saved, timeout):

    """
    This function is used by test cases that have two publishers and one
    subscriber. This tests check how many samples are received by the
    subscriber application with different sizes.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern.
    """
    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    sub_string = re.search('\w\s+\w+\s+[0-9]+ [0-9]+ \[([0-9]+)\]',
        child_sub.before + child_sub.after)
    if sub_string is None:
        return ReturnCode.DATA_NOT_RECEIVED

    first_sample_size = int(sub_string.group(1))

    max_samples_received = MAX_SAMPLES_READ
    samples_read = 0
    ignore_first_samples = True
    retcode = ReturnCode.RECEIVING_FROM_ONE

    while sub_string is not None and samples_read < max_samples_received:
        current_sample_size = int(sub_string.group(1))

        if current_sample_size != first_sample_size:
            if ignore_first_samples:
                # the first time we receive a different size, ignore it
                # For example, if we receive samples of size 20, then only
                # samples of size 30, we have to return RECEIVING_FROM_ONE.
                # If after receiving samples of size 30, we receive samples of
                # size 20 again, then we return RECEIVING_FROM_BOTH.
                ignore_first_samples = False
                first_sample_size = current_sample_size
            else:
                retcode = ReturnCode.RECEIVING_FROM_BOTH
                break

        index = child_sub.expect(
            [
                '\[[0-9]+\]', # index = 0
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )

        if index == 1:
            break
        elif index == 2:
            return ReturnCode.DATA_NOT_RECEIVED

        samples_read += 1

        sub_string = re.search('\w\s+\w+\s+[0-9]+ [0-9]+ \[([0-9]+)\]',
            child_sub.before + child_sub.after)

    print(f'Samples read: {samples_read}')
    return retcode

def test_color_receivers(child_sub, samples_sent, last_sample_saved, timeout):

    """
    This function is used by test cases that have two publishers and one
    subscriber. This tests how many samples are received by the
    subscriber application with different colors.

    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern.
    """
    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

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
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )

        if index == 1:
            break
        elif index == 2:
            return ReturnCode.DATA_NOT_RECEIVED

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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.DATA_NOT_RECEIVED

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
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )
        if index == 1:
            # no more data to process
            break
        elif index == 2:
            produced_code = ReturnCode.DATA_NOT_RECEIVED
            break

        samples_read += 1

        # search the next received sample by the subscriber app
        sub_string = re.search('[0-9]+ [0-9]+ \[([0-9]+)\]',
            child_sub.before + child_sub.after)

    if samples_read == max_samples_received:
        produced_code = ReturnCode.OK

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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.DATA_NOT_RECEIVED

    instance_color = []
    instance_seq_num = []
    first_iteration = []
    samples_read_per_instance = 0
    max_samples_received = MAX_SAMPLES_READ

    while samples_read_per_instance < max_samples_received:
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
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )
        if index == 0:
            if sub_string is not None and sub_string.group(1) in instance_color:
                samples_read_per_instance += 1
        elif index == 1:
            # no more data to process
            break
        elif index == 2:
            return ReturnCode.DATA_NOT_RECEIVED

    if max_samples_received == samples_read_per_instance:
        produced_code = ReturnCode.OK

    print(f'Samples read per instance: {samples_read_per_instance}, instances: {instance_color}')
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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    # At this point, the subscriber app has already received one sample
    # Check deadline requested missed
    index = child_sub.expect([
            'on_requested_deadline_missed()', # index = 0
            pexpect.TIMEOUT, # index = 1
            pexpect.EOF # index = 2
        ],
        timeout)
    if index == 0:
        return ReturnCode.DEADLINE_MISSED
    elif index == 1:
        return ReturnCode.DATA_NOT_RECEIVED
    else:
        index = child_sub.expect([
            '\[[0-9]+\]', # index = 0
            pexpect.TIMEOUT, # index = 1
            pexpect.EOF # index = 2
        ],
        timeout)
        if index == 0:
            return ReturnCode.OK
        else:
            return ReturnCode.DATA_NOT_RECEIVED

def test_reading_1_sample_every_10_samples_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests whether the subscriber application receives one sample
    out of 10 (for each instance). For example, first sample received with size
    5, the next one should have size [15,24], then [25,34], etc.
    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.DATA_NOT_RECEIVED

    instance_color = []
    instance_seq_num = []
    first_iteration = []
    ignore_first_sample = []
    max_samples_received = MAX_SAMPLES_READ / 20 # 25
    samples_read_per_instance = 0

    while samples_read_per_instance < max_samples_received:

        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[([0-9]+)\]',
            child_sub.before + child_sub.after)

        if sub_string is not None:
            # add a new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))
                instance_seq_num.append(int(sub_string.group(2)))
                first_iteration.append(True)
                ignore_first_sample.append(True)

            if sub_string.group(1) in instance_color:
                index = instance_color.index(sub_string.group(1))
                if first_iteration[index]:
                    first_iteration[index] = False
                else:
                    current_seq_num = int(sub_string.group(2))
                    if ignore_first_sample[index]:
                        ignore_first_sample[index] = False
                    else:
                        # check that the received sample reads only one sample in
                        # in the period of 10 samples. For example, if the previous
                        # sample received has size 5, the next one should be
                        # between [15-24], both included
                        if current_seq_num <= (instance_seq_num[index] + 9) or current_seq_num > instance_seq_num[index] + 19:
                            produced_code = ReturnCode.DATA_NOT_CORRECT
                            break
                    instance_seq_num[index] = current_seq_num
            else:
                produced_code = ReturnCode.DATA_NOT_CORRECT
                break

        # Get the next sample the subscriber is receiving
        index = child_sub.expect(
            [
                '\[[0-9]+\]', # index = 0
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )
        if index == 0:
            if sub_string is not None and sub_string.group(1) == instance_color[0]:
                # increase samples_read_per_instance only for the first instance
                samples_read_per_instance += 1
        elif index == 1:
            # no more data to process
            break
        elif index == 2:
            return ReturnCode.DATA_NOT_RECEIVED

    if max_samples_received == samples_read_per_instance:
        produced_code = ReturnCode.OK

    print(f'Samples read per instance: {samples_read_per_instance}, instances: {instance_color}')
    return produced_code

def test_unregistering_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests whether instances are correctly unregistered
    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.OK

    instance_color = []
    unregistered_instance_color = []
    max_samples_received = MAX_SAMPLES_READ
    samples_read_per_instance = 0

    while samples_read_per_instance < max_samples_received:
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
            if sub_string is not None and sub_string.group(1) not in unregistered_instance_color:
                unregistered_instance_color.append(sub_string.group(1))
                if len(instance_color) == len(unregistered_instance_color):
                    break
        # Get the next sample the subscriber is receiving or unregister/dispose
        index = child_sub.expect(
            [
                r'\w+\s+\w+\s+.*?\n', # index = 0
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )
        if index == 0:
            if sub_string is not None and sub_string.group(1) == instance_color[0]:
                samples_read_per_instance += 1
        elif index == 1:
            # no more data to process
            break
        elif index == 2:
            return ReturnCode.DATA_NOT_RECEIVED

    # compare that arrays contain the same elements and are not empty
    if len(instance_color) == 0:
        produced_code = ReturnCode.DATA_NOT_RECEIVED
    elif set(instance_color) == set(unregistered_instance_color):
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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.OK

    instance_color = []
    disposed_instance_color = []
    max_samples_received = MAX_SAMPLES_READ
    samples_read_per_instance = 0

    while samples_read_per_instance < max_samples_received:
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
            if sub_string is not None and sub_string.group(1) not in disposed_instance_color:
                disposed_instance_color.append(sub_string.group(1))
                if len(instance_color) == len(disposed_instance_color):
                    break
        # Get the next sample the subscriber is receiving or unregister/dispose
        index = child_sub.expect(
            [
                r'\w+\s+\w+\s+.*?\n', # index = 0
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )
        if index == 0:
            if sub_string is not None and sub_string.group(1) == instance_color[0]:
                samples_read_per_instance += 1
        elif index == 1:
            # no more data to process
            break
        elif index == 2:
            return ReturnCode.DATA_NOT_RECEIVED

    # compare that arrays contain the same elements and are not empty
    if len(instance_color) == 0:
        produced_code = ReturnCode.DATA_NOT_RECEIVED
    elif set(instance_color) == set(disposed_instance_color):
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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.DATA_NOT_RECEIVED
    samples_read = 0

    while samples_read < MAX_SAMPLES_READ:
        # As the interoperability_report is just looking for the size [<size>],
        # this does not count the data after it, we need to read a full sample
        index = child_sub.expect(
            [
                r'\w+\s+\w+\s+[0-9]+\s+[0-9]+\s+\[[0-9]+\]\s+\{[0-9]+\}', # index = 0
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
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
                if int(sub_string.group(1)) != 255:
                    produced_code = ReturnCode.DATA_NOT_CORRECT
                    break
                samples_read += 1
            else:
                produced_code = ReturnCode.DATA_NOT_CORRECT
                break
        elif index == 1 or index == 2:
            produced_code = ReturnCode.DATA_NOT_RECEIVED
            break

    if samples_read == MAX_SAMPLES_READ:
        produced_code = ReturnCode.OK

    print(f'Samples read: {samples_read}')

    return produced_code

def test_lifespan_2_3_consecutive_samples_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests that lifespan works correctly. In the test situation,
    only 2 or 3 consecutive samples should be received each time the reader
    reads data.
    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.DATA_NOT_RECEIVED

    # as the test is reading in a slower rate, reduce the number of samples read
    max_samples_lifespan = MAX_SAMPLES_READ / 10 # 50

    instance_color = []
    previous_seq_num = []
    first_iteration = []
    samples_read_per_instance = 0
    consecutive_samples = []
    ignore_first_sample = []

    while samples_read_per_instance < max_samples_lifespan:
        sub_string = re.search(r'\w+\s+(\w+)\s+[0-9]+\s+[0-9]+\s+\[([0-9]+)\]',
            child_sub.before + child_sub.after)

        if sub_string is not None:
            # add a new instance to instance_color
            if sub_string.group(1) not in instance_color:
                instance_color.append(sub_string.group(1))
                previous_seq_num.append(int(sub_string.group(2)))
                first_iteration.append(True)
                consecutive_samples.append(1) # take into account the first sample
                ignore_first_sample.append(True)

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
                        # if found consecutive samples, do not ignore the first sample
                        ignore_first_sample[index] = False
                    else:
                        # if the sequence number is not consecutive, check that we
                        # receive only 3 or 2 samples
                        if consecutive_samples[index] == 3 or consecutive_samples[index] == 2:
                            # reset value to 1, as this test consider that the first
                            # sample is consecutive with itself
                            consecutive_samples[index] = 1
                            produced_code = ReturnCode.OK
                        else:
                            if ignore_first_sample[index]:
                                # there may be a case in which we receive a sample
                                # and the next one is not consecutive, if that is the
                                # case, ignore it
                                ignore_first_sample[index] = False
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
                pexpect.TIMEOUT, # index = 1
                pexpect.EOF # index = 2
            ],
            timeout
        )
        if index == 0:
            if sub_string.group(1) == instance_color[0]:
                # increase samples_read_per_instance only for the first instance
                samples_read_per_instance += 1
            print(f'{child_sub.before + child_sub.after}')
        elif index == 1:
            # no more data to process
            break
        elif index == 2:
            return ReturnCode.DATA_NOT_RECEIVED

    if max_samples_lifespan == samples_read_per_instance:
        produced_code = ReturnCode.OK

    print(f'Samples read: {samples_read_per_instance}, instances: {instance_color}')
    return produced_code

def ordered_access_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests that ordered access works correctly. This counts the
    samples received in order and detects whether they are from the same instance
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

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.OK

    instance_color = []
    samples_read_per_instance = 0
    previous_sample_color = None
    color_different_count = 0
    color_equal_count = 0
    samples_printed = False
    ordered_access_group_count = 0

    while samples_read_per_instance < MAX_SAMPLES_READ:
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
                '\[[0-9]+\]', # index = 0
                r'Reading with ordered access.*?\n', # index = 1
                pexpect.TIMEOUT, # index = 2
                pexpect.EOF # index = 3
            ],
            timeout
        )
        if index == 0:
            if sub_string is not None and sub_string.group(1) in instance_color:
                samples_read_per_instance += 1
        elif index == 1:
            ordered_access_group_count += 1
        elif index == 2:
            # no more data to process
            break
        elif index == 3:
            produced_code = ReturnCode.DATA_NOT_RECEIVED
            break

        # Exit condition in case there are no samples being printed
        if ordered_access_group_count > MAX_SAMPLES_READ:
            # If we have not read enough samples, we consider it a failure
            if samples_read_per_instance <= MAX_SAMPLES_READ:
                produced_code = ReturnCode.DATA_NOT_RECEIVED
            break

    print(f'Samples read per instance: {samples_read_per_instance}, instances: {instance_color}')
    return produced_code

def coherent_sets_w_instances(child_sub, samples_sent, last_sample_saved, timeout):
    """
    This function tests that coherent sets works correctly. This counts the
    consecutive samples received from the same instance. The value should be 3
    as this is the coherent set count that the test is setting.
    Note: when using GROUP_PRESENTATION, the first iteration may print more
    samples (more coherent sets), the test checks that the samples received per
    instance is a multiple of 3, so the coherent sets are received complete.
    child_sub: child program generated with pexpect
    samples_sent: not used
    last_sample_saved: not used
    timeout: time pexpect waits until it matches a pattern
    """

    basic_check_retcode = basic_check(child_sub, samples_sent, last_sample_saved, timeout)

    if basic_check_retcode != ReturnCode.OK:
        return basic_check_retcode

    produced_code = ReturnCode.DATA_NOT_RECEIVED

    topics = {}
    samples_read_per_instance = 0
    previous_sample_color = None
    new_coherent_set_read = False
    first_time_reading = True
    ignore_firsts_coherent_set = 2
    coherent_sets_count = 0

    while samples_read_per_instance < MAX_SAMPLES_READ:
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
                if ignore_firsts_coherent_set != 0 and new_coherent_set_read:
                    ignore_firsts_coherent_set -= 1
                    for topic in topics:
                        for color in topics[topic]:
                            topics[topic][color] = 1
                elif new_coherent_set_read:
                    # the test is only ok if it has received coherent sets
                    produced_code = ReturnCode.OK
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
                    first_time_reading = False
                new_coherent_set_read = False

        # Get the next sample the subscriber is receiving or the next
        # 'Reading with ordered access message'
        index = child_sub.expect(
            [
                '\[[0-9]+\]', # index = 0
                r'Reading coherent sets.*?\n', # index = 1
                pexpect.TIMEOUT, # index = 2
                pexpect.EOF # index = 3
            ],
            timeout
        )
        if index == 0:
            if sub_string is not None and sub_string.group(2) in topics[sub_string.group(1)]:
                samples_read_per_instance += 1
        elif index == 1:
            coherent_sets_count += 1
        elif index == 2:
            # no more data to process
            break
        elif index == 3:
            produced_code = ReturnCode.DATA_NOT_RECEIVED
            break

        # Exit condition in case there are no samples being printed
        if coherent_sets_count > MAX_SAMPLES_READ:
            # If we have not read enough samples, we consider it a failure
            if samples_read_per_instance <= MAX_SAMPLES_READ:
                produced_code = ReturnCode.DATA_NOT_RECEIVED
            break

    print(f'Samples read per instance: {samples_read_per_instance}')
    print("Instances:")
    for topic in topics:
        print(f"Topic {topic}: {', '.join(topics[topic].keys())}")

    return produced_code
