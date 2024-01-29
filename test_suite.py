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
#       'name' : [[parameter_list], [expected_return_code_list], checking_function]
# where:
#       * name: TestCase's name
#       * parameter_list: list in which each element is the parameters that
#         the shape_main application will use.
#       * expected_return_code_list: list with expected ReturnCodes
#         for a succeed test execution.
#       * checking_function [OPTIONAL]: function to check how the Subscribers receive
#         the samples from the Publishers. By default, it just checks that
#         the data is received. In case that it has a different behavior, that
#         function must be implemented in the test_suite file and the test case
#         should reference it in this parameter.
# The number of elements in parameter_list defines how many shape_main
# applications the interoperability_report will run. It should be the same as
# the number of elements in expected_return_code_list.


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
    max_samples_received = 125

    for x in range(0, max_samples_received, 1):
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

    return ReturnCode.RECEIVING_FROM_ONE


def test_reliability_4(child_sub, samples_sent, timeout):
    """
    This function tests reliability, it checks whether the Subscriber receives
    the samples in order.

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
    while sub_string is not None:
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
        # search the next received sample by the subscriber app
        sub_string = re.search('[0-9]+ [0-9]+ \[[0-9]+\]',
            child_sub.before + child_sub.after)

    return produced_code


def test_durability_volatile(child_sub, samples_sent, timeout):
    """
    This function tests the volatile durability, it checks that the sample the
    Subscriber receives is not the first one. The Publisher application sends
    samples increasing the value of the size, so if the first sample that the
    Subscriber app doesn't have the size == 1, the test is correct.

    child_sub: child program generated with pexpect
    samples_sent: list of multiprocessing Queues with the samples
                the Publishers send. Element 1 of the list is for
                Publisher 1, etc.
    timeout: time pexpect waits until it matches a pattern.
    """

    # Read the first sample, if it has the size == 1, it is using transient
    # local durability correctly
    sub_string = re.search('[0-9]+ [0-9]+ \[([0-9]+)\]',
        child_sub.before + child_sub.after)

    # Check if the element received is not the first 5 samples (aka size >= 5)
    # which should not be the case. Checking 5 samples instead of just one to
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
    samples_sent: list of multiprocessing Queues with the samples
                the Publishers send. Element 1 of the list is for
                Publisher 1, etc.
    timeout: time pexpect waits until it matches a pattern.
    """

    # Read the first sample, if it has the size != 1, it is using volatile
    # durability correctly
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


def test_deadline_4(child_sub, samples_sent, timeout):
    """
    This function tests the volatile durability, it checks that the sample the
    Subscriber receives is not the first one. The Publisher application sends
    samples increasing the value of the size, so if the first sample that the
    Subscriber app doesn't have the size == 1, the test is correct.

    child_sub: child program generated with pexpect
    samples_sent: list of multiprocessing Queues with the samples
                the Publishers send. Element 1 of the list is for
                Publisher 1, etc.
    timeout: time pexpect waits until it matches a pattern.
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
    'Test_DataRepresentation_0' : [['-P -t Square -x 1', '-S -t Square -x 1'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_DataRepresentation_1' : [['-P -t Square -x 1', '-S -t Square -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_DataRepresentation_2' : [['-P -t Square -x 2', '-S -t Square -x 1'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_DataRepresentation_3' : [['-P -t Square -x 2', '-S -t Square -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # DOMAIN
    'Test_Domain_0' : [['-P -t Square', '-S -t Square'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Domain_1' : [['-P -t Square', '-S -t Square -d 1'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Domain_2' : [['-P -t Square -d 1', '-S -t Square'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Domain_3' : [['-P -t Square -d 1', '-S -t Square -d 1'], [ReturnCode.OK, ReturnCode.OK]],

    # RELIABILITY
    'Test_Reliability_0' : [['-P -t Square -b', '-S -t Square -b'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Reliability_1' : [['-P -t Square -b', '-S -t Square -r'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Reliability_2' : [['-P -t Square -r', '-S -t Square -b'], [ReturnCode.OK, ReturnCode.OK]],
    # This test only checks that data is received correctly
    'Test_Reliability_3' : [['-P -t Square -r -k 3', '-S -t Square -r'], [ReturnCode.OK, ReturnCode.OK]],
    # This test checks that data is received in the right order
    'Test_Reliability_4' : [['-P -t Square -r -k 0 -w', '-S -t Square -r -k 0'], [ReturnCode.OK, ReturnCode.OK], test_reliability_4],

    # DEADLINE
    'Test_Deadline_0' : [['-P -t Square -f 3', '-S -t Square -f 5'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Deadline_1' : [['-P -t Square -f 5', '-S -t Square -f 5'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Deadline_2' : [['-P -t Square -f 7', '-S -t Square -f 5'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    # This test checks that the deadline is missed in both, publisher and subscriber
    # because the write-period is higher than the deadline period, that means
    # that the samples won't be send and received on time
    'Test_Deadline_4' : [['-P -t Square -w -f 2 --write-period 3000', '-S -t Square -f 2'], [ReturnCode.DEADLINE_MISSED, ReturnCode.DEADLINE_MISSED], test_deadline_4],

    # TOPIC
    'Test_Topic_0' : [['-P -t Square', '-S -t Square'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Topic_1' : [['-P -t Square', '-S -t Circle'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Topic_2' : [['-P -t Circle', '-S -t Square'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Topic_3' : [['-P -t Circle', '-S -t Circle'], [ReturnCode.OK, ReturnCode.OK]],

    # COLOR
    'Test_Color_0' : [['-P -t Square -c BLUE', '-S -t Square -c BLUE'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_1' : [['-P -t Square -c BLUE', '-S -t Square -c RED'], [ReturnCode.OK, ReturnCode.DATA_NOT_RECEIVED]],
    'Test_Color_2' : [['-P -t Square -c BLUE', '-S -t Square'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_3' : [['-P -t Square -c RED', '-S -t Square -c BLUE'], [ReturnCode.OK, ReturnCode.DATA_NOT_RECEIVED]],
    'Test_Color_4' : [['-P -t Square -c RED', '-S -t Square -c RED'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_5' : [['-P -t Square -c RED', '-S -t Square'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_6' : [['-P -t Square', '-S -t Square -c BLUE'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_7' : [['-P -t Square', '-S -t Square -c RED'], [ReturnCode.OK, ReturnCode.DATA_NOT_RECEIVED]],
    'Test_Color_8' : [['-P -t Square', '-S -t Square'], [ReturnCode.OK, ReturnCode.OK]],

    # PARTITION
    'Test_Partition_0' : [['-P -t Square -p "p1"', '-S -t Square -p "p1"'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Partition_1' : [['-P -t Square -p "p1"', '-S -t Square -p "p2"'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Partition_2' : [['-P -t Square -p "p2"', '-S -t Square -p "p1"'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],

    # DURABILITY
    'Test_Durability_0' : [['-P -t Square -D v', '-S -t Square -D v'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_1' : [['-P -t Square -D v', '-S -t Square -D l'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Durability_2' : [['-P -t Square -D v', '-S -t Square -D t'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Durability_3' : [['-P -t Square -D v', '-S -t Square -D p'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    'Test_Durability_4' : [['-P -t Square -D l', '-S -t Square -D v'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_5' : [['-P -t Square -D l', '-S -t Square -D l'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_6' : [['-P -t Square -D l', '-S -t Square -D t'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Durability_7' : [['-P -t Square -D l', '-S -t Square -D p'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    'Test_Durability_8' : [['-P -t Square -D t', '-S -t Square -D v'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_9' : [['-P -t Square -D t', '-S -t Square -D l'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_10': [['-P -t Square -D t', '-S -t Square -D t'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_11': [['-P -t Square -D t', '-S -t Square -D p'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    'Test_Durability_12' : [['-P -t Square -D p', '-S -t Square -D v'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_13' : [['-P -t Square -D p', '-S -t Square -D l'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_14' : [['-P -t Square -D p', '-S -t Square -D t'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_15' : [['-P -t Square -D p', '-S -t Square -D p'], [ReturnCode.OK, ReturnCode.OK]],

    # Test durability behavior
    # This test sends all samples with reliable reliability and check that the
    # first sample that the subscriber app reads are not the first one
    # (the interoperability_test waits 1 second before creating the second
    # entity, the subscriber, if durability is set)
    'Test_Durability_16' : [['-P -t Square -z 0 -r -k 0 -D v -w', '-S -t Square -r -k 0 -D v'], [ReturnCode.OK, ReturnCode.OK], test_durability_volatile],
    # This test checks that the subscriber application reads the first sample that
    # have been sent by the publisher before creating the subscriber
    'Test_Durability_17' : [['-P -t Square -z 0 -r -k 0 -D t -w', '-S -t Square -r -k 0 -D t'], [ReturnCode.OK, ReturnCode.OK], test_durability_transient_local],

    # HISTORY
    'Test_History_0' : [['-P -t Square -k 3', '-S -t Square -k 3'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_History_1' : [['-P -t Square -k 3', '-S -t Square -k 0'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_History_2' : [['-P -t Square -k 0', '-S -t Square -k 3'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_History_3' : [['-P -t Square -k 0', '-S -t Square -k 0'], [ReturnCode.OK, ReturnCode.OK]],

    # OWNERSHIP
    'Test_Ownership_0': [['-P -t Square -s -1', '-S -t Square -s -1'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Ownership_1': [['-P -t Square -s -1', '-S -t Square -s 1'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Ownership_2': [['-P -t Square -s 3', '-S -t Square -s -1'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    # For Test_Ownership_[3|4|5|6]: each publisher application publishes samples
    # with a different shapesize to allow the subscriber app to recognize from
    # which Publisher is receiving the samples.

    # The DataReader should receive from both publisher apps because they
    # publish different instances and the ownership is applied per instance.
    'Test_Ownership_3': [['-P -t Square -s 3 -r -k 0 -c BLUE -w -z 20',
                          '-P -t Square -s 4 -r -k 0 -c RED -w -z 30',
                          '-S -t Square -s 1 -r -k 0'],
                         [ReturnCode.OK,
                          ReturnCode.OK,
                          ReturnCode.RECEIVING_FROM_BOTH],
                        test_ownership_receivers],

    # The DataReader should only receive samples from the DataWriter with higher
    # ownership. There may be the situation that the DataReader starts receiving
    # samples from one DataWriter until another DataWriter with higher ownership
    # strength is created. This should be handled by test_ownership_receivers().
    'Test_Ownership_4': [['-P -t Square -s 3 -r -k 0 -c BLUE -w -z 20',
                          '-P -t Square -s 4 -r -k 0 -c BLUE -w -z 30',
                          '-S -t Square -s 1 -r -k 0'],
                         [ReturnCode.OK,
                          ReturnCode.OK,
                          ReturnCode.RECEIVING_FROM_ONE],
                         test_ownership_receivers],

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_5': [['-P -t Square -s -1 -r -k 0 -c BLUE -w -z 20',
                          '-P -t Square -s -1 -r -k 0 -c RED -w -z 30',
                          '-S -t Square -s -1 -r -k 0'],
                         [ReturnCode.OK,
                          ReturnCode.OK,
                          ReturnCode.RECEIVING_FROM_BOTH],
                        test_ownership_receivers],

    # The DataReader should receive from both publisher apps because they have
    # shared ownership.
    'Test_Ownership_6': [['-P -t Square -s -1 -r -k 0 -c BLUE -w -z 20',
                          '-P -t Square -s -1 -r -k 0 -c BLUE -w -z 30',
                          '-S -t Square -s -1 -r -k 0'],
                         [ReturnCode.OK,
                          ReturnCode.OK,
                          ReturnCode.RECEIVING_FROM_BOTH],
                        test_ownership_receivers],
}
