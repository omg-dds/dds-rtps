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


def test_ownership3_4(child_sub, samples_sent, timeout):

    """"
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
        sub_string = re.search('[0-9]{3} [0-9]{3} \[[0-9]{2}\]',
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
                '\[[0-9]{2}\]', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            break

        if x == 0:
            # A potential case is that the reader gets data from one writer and
            # then start receiving from a different writer with a higher
            # ownership. This avoids returning RECEIVING_FROM_BOTH if this is
            # the case.
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
    max_samples_received = 3
    max_wait_time = 5
    for x in range(0, max_samples_received, 1):
        # take the position of the samples
        sub_string = re.search('[0-9]{3} [0-9]{3} \[[0-9]{2}\]',
            child_sub.before + child_sub.after)
        # the function takes the samples the first publisher is sending
        # ('samples_sent[0]') and checks whether they match the
        # samples that the subscriber has received.
        # In the case that 'samples_sent[0]' is empty, the method get()
        # waits <max_wait_time> to stop the execution of the loop.
        try:
            if samples_sent[0].get(block=True,timeout=max_wait_time) == sub_string.group(0):
                produced_code = ReturnCode.OK
            else:
                produced_code = ReturnCode.DATA_NOT_CORRECT
                break
        except:
            print("No samples to take from Queue")
            break

        # Get the next samples the subscriber is receiving
        child_sub.expect(
            [
                '\[[0-9]{2}\]', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
    return produced_code

rtps_test_suite_1 = {
    # DATA REPRESENTATION
    'Test_DataRepresentation_0' : [['-P -t Square -x 1', '-S -t Square -x 1'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_DataRepresentation_1' : [['-P -t Square -x 1', '-S -t Square -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_DataRepresentation_2' : [['-P -t Square -x 2', '-S -t Square -x 1'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_DataRepresentation_3' : [['-P -t Square -x 2', '-S -t Square -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # DOMAIN
    'Test_Domain_0' : [['-P -t Square -x 2', '-S -t Square -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Domain_1' : [['-P -t Square -x 2', '-S -t Square -d 1 -x 2'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Domain_2' : [['-P -t Square -d 1 -x 2', '-S -t Square -x 2'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Domain_3' : [['-P -t Square -d 1 -x 2', '-S -t Square -d 1 -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # RELIABILITY
    'Test_Reliability_0' : [['-P -t Square -b -x 2', '-S -t Square -b -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Reliability_1' : [['-P -t Square -b -x 2', '-S -t Square -r -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Reliability_2' : [['-P -t Square -r -x 2', '-S -t Square -b -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    # This test only checks that data is received correctly
    'Test_Reliability_3' : [['-P -t Square -r -k 3 -x 2', '-S -t Square -r -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    # This test checks that data is received in the right order
    'Test_Reliability_4' : [['-P -t Square -r -k 0 -w -x 2', '-S -t Square -r -k 0 -x 2'], [ReturnCode.OK, ReturnCode.OK], test_reliability_4],

    # DEADLINE
    'Test_Deadline_0' : [['-P -t Square -f 3 -x 2', '-S -t Square -f 5 -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Deadline_1' : [['-P -t Square -f 5 -x 2', '-S -t Square -f 5 -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Deadline_2' : [['-P -t Square -f 7 -x 2', '-S -t Square -f 5 -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    # TOPIC
    'Test_Topic_0' : [['-P -t Square -x 2', '-S -t Square -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Topic_1' : [['-P -t Square -x 2', '-S -t Circle -x 2'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Topic_2' : [['-P -t Circle -x 2', '-S -t Square -x 2'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Topic_3' : [['-P -t Circle -x 2', '-S -t Circle -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # COLOR
    'Test_Color_0' : [['-P -t Square -c BLUE -x 2', '-S -t Square -c BLUE -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_1' : [['-P -t Square -c BLUE -x 2', '-S -t Square -c RED -x 2'], [ReturnCode.OK, ReturnCode.DATA_NOT_RECEIVED]],
    'Test_Color_2' : [['-P -t Square -c BLUE -x 2', '-S -t Square -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_3' : [['-P -t Square -c RED -x 2', '-S -t Square -c BLUE -x 2'], [ReturnCode.OK, ReturnCode.DATA_NOT_RECEIVED]],
    'Test_Color_4' : [['-P -t Square -c RED -x 2', '-S -t Square -c RED -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_5' : [['-P -t Square -c RED -x 2', '-S -t Square -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_6' : [['-P -t Square -x 2', '-S -t Square -c BLUE -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Color_7' : [['-P -t Square -x 2', '-S -t Square -c RED -x 2'], [ReturnCode.OK, ReturnCode.DATA_NOT_RECEIVED]],
    'Test_Color_8' : [['-P -t Square -x 2', '-S -t Square -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # PARTITION
    'Test_Partition_0' : [['-P -t Square -p "p1" -x 2', '-S -t Square -p "p1" -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Partition_1' : [['-P -t Square -p "p1" -x 2', '-S -t Square -p "p2" -x 2'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Partition_2' : [['-P -t Square -p "p2" -x 2', '-S -t Square -p "p1" -x 2'], [ReturnCode.READER_NOT_MATCHED, ReturnCode.WRITER_NOT_MATCHED]],
    'Test_Partition_3' : [['-P -t Square -p "p2" -x 2', '-S -t Square -p "p2" -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # DURABILITY
    'Test_Durability_0' : [['-P -t Square -D v -x 2', '-S -t Square -D v -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_1' : [['-P -t Square -D v -x 2', '-S -t Square -D l -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Durability_2' : [['-P -t Square -D v -x 2', '-S -t Square -D t -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Durability_3' : [['-P -t Square -D v -x 2', '-S -t Square -D p -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    'Test_Durability_4' : [['-P -t Square -D l -x 2', '-S -t Square -D v -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_5' : [['-P -t Square -D l -x 2', '-S -t Square -D l -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_6' : [['-P -t Square -D l -x 2', '-S -t Square -D t -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Durability_7' : [['-P -t Square -D l -x 2', '-S -t Square -D p -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    'Test_Durability_8' : [['-P -t Square -D t -x 2', '-S -t Square -D v -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_9' : [['-P -t Square -D t -x 2', '-S -t Square -D l -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_10': [['-P -t Square -D t -x 2', '-S -t Square -D t -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_11': [['-P -t Square -D t -x 2', '-S -t Square -D p -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],

    'Test_Durability_12' : [['-P -t Square -D p -x 2', '-S -t Square -D v -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_13' : [['-P -t Square -D p -x 2', '-S -t Square -D l -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_14' : [['-P -t Square -D p -x 2', '-S -t Square -D t -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Durability_15' : [['-P -t Square -D p -x 2', '-S -t Square -D p -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # HISTORY
    'Test_History_0' : [['-P -t Square -k 3 -x 2', '-S -t Square -k 3 -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_History_1' : [['-P -t Square -k 3 -x 2', '-S -t Square -k 0 -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_History_2' : [['-P -t Square -k 0 -x 2', '-S -t Square -k 3 -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_History_3' : [['-P -t Square -k 0 -x 2', '-S -t Square -k 0 -x 2'], [ReturnCode.OK, ReturnCode.OK]],

    # OWNERSHIP
    'Test_Ownership_0': [['-P -t Square -s -1 -x 2', '-S -t Square -s -1 -x 2'], [ReturnCode.OK, ReturnCode.OK]],
    'Test_Ownership_1': [['-P -t Square -s -1 -x 2', '-S -t Square -s 3 -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    'Test_Ownership_2': [['-P -t Square -s 3 -x 2', '-S -t Square -s -1 -x 2'], [ReturnCode.INCOMPATIBLE_QOS, ReturnCode.INCOMPATIBLE_QOS]],
    # Two Publishers and One Subscriber to test that if each one has a different color, the ownership strength does not matter.
    # Each Publisher has a different shapesize to allow the Subscriber to recognize from which Publisher is receiving the samples.
    'Test_Ownership_3': [['-P -t Square -s 3 -c BLUE -w -x 2 -z 20', '-P -t Square -s 4 -c RED -w -x 2 -z 30', '-S -t Square -s 2 -r -k 0 -x 2'],
                         [ReturnCode.OK, ReturnCode.OK, ReturnCode.RECEIVING_FROM_BOTH], test_ownership3_4],
    # Two Publishers and One Subscriber to test that the Subscriber only receives samples from the Publisher with the greatest ownership.
    # Each Publisher has a different shapesize to allow the Subscriber to recognize from which Publisher is receiving the samples.
    'Test_Ownership_4': [['-P -t Square -s 5 -r -k 0 -w -x 2 -z 20', '-P -t Square -s 4 -r -k 0 -w -x 2 -z 30', '-S -t Square -s 2 -r -k 0 -x 2'],
                         [ReturnCode.OK, ReturnCode.OK, ReturnCode.RECEIVING_FROM_ONE], test_ownership3_4],
}
