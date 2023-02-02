#!/usr/bin/python

import time
import re
import pexpect
import argparse
from junitparser import TestCase, TestSuite, JUnitXml, Attr, Failure
from multiprocessing import Process, Queue, Manager, Event
from datetime import datetime
import tempfile
from os.path import exists

from rtps_test_utilities import ReturnCode
from test_suite import rtps_test_suite_1

def log_message(message, verbosity):
    if verbosity:
        print(message)

def run_subscriber_shape_main(
        name_executable: str,
        parameters: str,
        test_name: str,
        produced_code: "list[int]",
        produced_code_index: int,
        samples_sent: Queue,
        verbosity: bool,
        timeout: int,
        file: tempfile.TemporaryFile,
        subscriber_finished: Event,
        publisher_finished: Event):

    """ This function runs the subscriber application with
        the specified parameters. Then it saves the
        return code in the variable produced_code.

        name_executable <<in>>: name of the shape_main application to run
                as a Subscriber
        parameters <<in>>: shape_main application parameter list
        test_name <<in>>: name of the test that is being tested
        produced_code <<out>>: this variable will be overwritten with
                the obtained ReturnCode
        produced_code_index <<in>>: index of the produced_code list
                where the ReturnCode is saved
        samples_sent <<in>>: this variable contains the samples
                the Publisher sends
        verbosity <<in>>: print debug information
        timeout <<in>>: time pexpect waits until it matches a pattern
        file <<inout>>: temporal file to save shape_main application output
        subscriber_finished <<inout>>: object event from multiprocessing
                that is set when the subscriber is finished
        publisher_finished <<inout>>: object event from multiprocessing
                that is set when the publisher is finished

        The function runs the Shape Application as a Subscriber
        with the parameters defined.
        The Subscriber Shape Application follows the next steps:
            * The topic is created
            * The Data Reader is created
            * The Data Reader matches with a Data Writer
            * The Data Reader detects the Data Writer as alive
            * The Data Reader receives data

        If the Shape Application passes one step, it prints a specific
        string pattern. This function matches that pattern and and waits
        for the next input string from the Shape Application. If the
        ShapeApplication stops at some step, it prints an error message.
        When this function matches an error string (or doesn't match
        an expected pattern in the specified timeout),
        the corresponding ReturnCode is saved in
        produced_code[produced_code_index] and the process finishes.

    """
    # Step 1 : run the executable
    log_message('Running Shape Application Subscriber', verbosity)
    child_sub = pexpect.spawnu(f'{name_executable} {parameters}')
    child_sub.logfile = file

    # Step 2 : Check if the topic is created
    log_message('S: Waiting for topic creation', verbosity)
    index = child_sub.expect(
        [
            'Create topic:', # index = 0
            pexpect.TIMEOUT, # index = 1
            'please specify topic name', # index = 2
            'unrecognized value', # index = 3
            pexpect.EOF # index = 4
        ],
        timeout
    )

    if index == 1 or index == 2 or index == 4:
        produced_code[produced_code_index] = ReturnCode.TOPIC_NOT_CREATED
    elif index == 3:
        produced_code[produced_code_index] = ReturnCode.UNRECOGNIZED_VALUE
    elif index == 0:
        # Step 3 : Check if the reader is created
        log_message('S: Waiting for DR creation', verbosity)
        index = child_sub.expect(
            [
                'Create reader for topic:', # index = 0
                pexpect.TIMEOUT, # index = 1
                'failed to create content filtered topic' # index = 2
            ],
            timeout
        )

        if index == 1:
            produced_code[produced_code_index] = ReturnCode.READER_NOT_CREATED
        elif index == 2:
            produced_code[produced_code_index] = ReturnCode.FILTER_NOT_CREATED
        elif index == 0:
            # Step 4 : Check if the reader matches the writer
            log_message('S: Waiting for DW matching', verbosity)
            index = child_sub.expect(
                [
                    'on_subscription_matched()', # index = 0
                    pexpect.TIMEOUT, # index = 1
                    'on_requested_incompatible_qos()' # index = 2
                ],
                timeout
            )

            if index == 1:
                produced_code[produced_code_index] = ReturnCode.WRITER_NOT_MATCHED
            elif index == 2:
                produced_code[produced_code_index] = ReturnCode.INCOMPATIBLE_QOS
            elif index == 0:
                # Step 5: Check if the reader detects the writer as alive
                log_message('S: Waiting for detecting DW alive', verbosity)
                index = child_sub.expect(
                    [
                        'on_liveliness_changed()', # index = 0
                        pexpect.TIMEOUT # index = 1
                    ],
                    timeout
                )

                if index == 1:
                    produced_code[produced_code_index] = ReturnCode.WRITER_NOT_ALIVE
                elif index == 0:
                    #Step 6 : Check if the reader receives the samples
                    log_message('S: Waiting for receiving samples', verbosity)
                    index = child_sub.expect(
                            [
                                '\[[0-9][0-9]\]', # index = 0
                                pexpect.TIMEOUT # index = 1
                            ],
                            timeout
                        )

                    if index == 1:
                        produced_code[produced_code_index] = ReturnCode.DATA_NOT_RECEIVED
                    elif index == 0:
                        # This test checks that data is received in the right order
                        if test_name == 'Test_Reliability_4':
                            for x in range(0, 3, 1):
                                sub_string = re.search('[0-9]{3} [0-9]{3}',
                                                        child_sub.before)
                                if samples_sent.get() == sub_string.group(0):
                                    produced_code[produced_code_index] = ReturnCode.OK
                                else:
                                    produced_code[produced_code_index] = ReturnCode.DATA_NOT_CORRECT
                                    break
                                log_message('S: Waiting for receiving samples',
                                            verbosity)
                                child_sub.expect(
                                            [
                                                '\[[0-9][0-9]\]', # index = 0
                                                pexpect.TIMEOUT # index = 1
                                            ],
                                            timeout
                                )
                        # Two Publishers and One Subscriber to test that if
                        # each one has a different color, the ownership strength
                        # does not matter
                        elif test_name == 'Test_Ownership_3':
                            red_received = False
                            blue_received = False
                            produced_code[produced_code_index] = ReturnCode.RECEIVING_FROM_ONE
                            for x in range(0,100,1):
                                sub_string_red = re.search('RED',
                                                        child_sub.before)
                                sub_string_blue = re.search('BLUE',
                                                        child_sub.before)

                                if sub_string_red != None:
                                    red_received = True

                                if sub_string_blue != None:
                                    blue_received = True

                                if blue_received and red_received:
                                    produced_code[produced_code_index] = ReturnCode.RECEIVING_FROM_BOTH
                                    break
                                log_message('S: Waiting for receiving samples',
                                            verbosity)
                                child_sub.expect(
                                            [
                                                '\[[0-9][0-9]\]', # index = 0
                                                pexpect.TIMEOUT # index = 1
                                            ],
                                            timeout
                                )
                        # Two Publishers and One Subscriber to test that
                        # the Subscriber only receives samples from
                        # the Publisher with the greatest ownership
                        elif test_name == 'Test_Ownership_4':
                            first_received = False
                            second_received = False
                            list_data_received_second = []
                            for x in range(0,80,1):
                                sub_string = re.search('[0-9]{3} [0-9]{3}',
                                                        child_sub.before)
                                try:
                                    list_data_received_second.append(samples_sent.get(True, 5))
                                except:
                                    break;
                                if sub_string.group(0) not in list_data_received_second:
                                    first_received = True
                                elif sub_string.group(0) in list_data_received_second \
                                            and first_received:
                                    second_received = True
                                    produced_code[produced_code_index] = ReturnCode.RECEIVING_FROM_BOTH
                                log_message('S: Waiting for receiving samples',
                                            verbosity)
                                child_sub.expect(
                                            [
                                                '\[[0-9][0-9]\]', # index = 0
                                                pexpect.TIMEOUT # index = 1
                                            ],
                                            timeout
                                )

                            if second_received == False:
                                produced_code[produced_code_index] = ReturnCode.RECEIVING_FROM_ONE

                        else:
                            produced_code[produced_code_index] = ReturnCode.OK

    subscriber_finished.set()   # set subscriber as finished
    log_message('S: Waiting for Publisher to finish', verbosity)
    publisher_finished.wait()   # wait for publisher to finish
    return


def run_publisher_shape_main(
        name_executable: str,
        parameters: str,
        test_name: str,
        produced_code: "list[int]",
        produced_code_index: int,
        samples_sent: Queue,
        verbosity: bool,
        timeout: int,
        file: tempfile.TemporaryFile,
        subscriber_finished: Event,
        publisher_finished: Event):

    """ This function runs the publisher application with
        the specified parameters. Then it saves the
        return code in the variable produced_code.

        name_executable: <<in>> name of the shape_main application to run
                as a Publisher
        parameters <<in>>: shape_main application parameter list
        test_name <<in>>: name of the test that is being tested
        produced_code <<out>>: this variable will be overwritten with
                the obtained ReturnCode
        produced_code_index <<in>>: index of the produced_code list
                where the ReturnCode is saved
        samples_sent <<out>>: this variable contains the samples
                the Publisher sends
        verbosity <<in>>: print debug information
        timeout <<in>>: time pexpect waits until it matches a pattern
        file <<inout>>: temporal file to save shape_main application output
        subscriber_finished <<inout>>: object event from multiprocessing
                that is set when the subscriber is finished
        publisher_finished <<inout>>: object event from multiprocessing
                that is set when the publisher is finished

        The function runs the Shape Application as a Publisher
        with the parameters defined.
        The Publisher Shape Application follows the next steps:
            * The topic is created
            * The Data Writer is created
            * The Data Writer matches with a Data Reader
            * The Data Writer sends data

        If the Shape Application passes one step, it prints a specific
        string pattern. This function matches that pattern and and waits
        for the next input string from the Shape Application. If the
        ShapeApplication stops at some step, it prints an error message.
        When this function matches an error string (or doesn't match
        an expected pattern in the specified timeout),
        the corresponding ReturnCode is saved in
        produced_code[produced_code_index] and the process finishes.
    """

    # Step 1 : run the executable
    log_message('Running Shape Application Publisher', verbosity)
    child_pub = pexpect.spawnu(f'{name_executable} {parameters}')
    child_pub.logfile = file

    # Step 2 : Check if the topic is created
    log_message('P: Waiting for topic creation', verbosity)
    index = child_pub.expect(
        [
            'Create topic:', # index == 0
            pexpect.TIMEOUT, # index == 1
            'please specify topic name', # index == 2
            'unrecognized value', # index == 3
            pexpect.EOF # index == 4
        ],
        timeout
    )

    if index == 1 or index == 2 or index == 4:
        produced_code[produced_code_index] = ReturnCode.TOPIC_NOT_CREATED
    elif index == 3:
        produced_code[produced_code_index] = ReturnCode.UNRECOGNIZED_VALUE
    elif index == 0:
        # Step 3 : Check if the writer is created
        log_message('P: Waiting for DW creation', verbosity)
        index = child_pub.expect(
            [
                'Create writer for topic', # index = 0
                pexpect.TIMEOUT # index = 1
            ],
            timeout
        )
        if index == 1:
            produced_code[produced_code_index] = ReturnCode.WRITER_NOT_CREATED
        elif index == 0:
            # Step 4 : Check if the writer matches the reader
            log_message('P: Waiting for DR matching', verbosity)
            index = child_pub.expect(
                [
                    'on_publication_matched()', # index = 0
                    pexpect.TIMEOUT, # index = 1
                    'on_offered_incompatible_qos' # index = 2
                ],
                timeout
            )
            if index == 1:
                produced_code[produced_code_index] = ReturnCode.READER_NOT_MATCHED
            elif index == 2:
                produced_code[produced_code_index] = ReturnCode.INCOMPATIBLE_QOS
            elif index == 0:
                if '-w' in parameters:
                    #Step  5: Check if the writer sends the samples
                    log_message('P: Waiting for sending samples', verbosity)
                    index = child_pub.expect(
                            [
                                '\[[0-9][0-9]\]', # index = 0
                                pexpect.TIMEOUT # index = 1
                            ],
                            timeout
                        )
                    if index == 0:
                        produced_code[produced_code_index] = ReturnCode.OK
                        # With these tests we check if we receive the data correctly,
                        # in order to do it we are saving the samples sent
                        if test_name == 'Test_Reliability_4' \
                                    or test_name == 'Test_Ownership_4':
                            for x in range(0, 80 ,1):
                                pub_string = re.search('[0-9]{3} [0-9]{3}',
                                                            child_pub.before )
                                samples_sent.put(pub_string.group(0))
                                log_message('P: Waiting for sending samples',
                                            verbosity)
                                child_pub.expect([
                                            '\[[0-9][0-9]\]', # index = 0
                                            pexpect.TIMEOUT # index = 1
                                                ],
                                            timeout
                                )

                    elif index == 1:
                        produced_code[produced_code_index] = ReturnCode.DATA_NOT_SENT
                else:
                    produced_code[produced_code_index] = ReturnCode.OK

    log_message('P: Waiting for Subscriber to finish', verbosity)
    subscriber_finished.wait() # wait for subscriber to finish
    publisher_finished.set()   # set publisher as finished
    return

def run_test(
        name_executable_pub: str,
        name_executable_sub: str,
        test_case: TestCase,
        param_pub: str,
        param_sub: str,
        expected_code_pub: ReturnCode,
        expected_code_sub: ReturnCode,
        verbosity: bool,
        timeout: int):

    """ Run the Publisher and the Subscriber and check the ReturnCode

        name_executable_pub <<in>>: name of the shape_main application to run
                as a Publisher
        name_executable_sub <<in>>: name of the shape_main application to run
                as a Subscriber
        test_case <<inout>>: testCase object to test
        param_pub <<in>>: shape_main application publisher parameter list
        param_sub <<in>>: shape_main application subscriber parameter list
        expected_code_pub <<in>>: ReturnCode the Publisher would obtain
                in a non error situation
        expected_code_sub <<in>>: ReturnCode the Subscriber would obtain
                in a non error situation
        verbosity <<in>>: print debug information
        timeout <<in>>: time pexpect waits until it matches a pattern

        The function runs two different processes: one publisher
        application and one subscriber application.
        Then it checks that the code obtained is the expected one.
    """
    log_message(f'run_test parameters: \
                    name_executable_pub: {name_executable_pub} \
                    name_executable_sub: {name_executable_sub} \
                    test_case: {test_case.name} \
                    param_pub: {param_pub} \
                    param_sub: {param_sub} \
                    expected_code_pub: {expected_code_pub} \
                    expected_code_sub: {expected_code_sub} \
                    verbosity: {verbosity} \
                    timeout: {timeout}',
                    verbosity)

    manager = Manager()
     # used for storing the obtained ReturnCode
     # (from Publisher and Subscriber)
    return_code = manager.list(range(2))
    data = Queue() # used for storing the samples

    subscriber_finished = Event()
    publisher_finished = Event()

    log_message('Creating temporary files', verbosity)
    file_publisher = tempfile.TemporaryFile(mode='w+t')
    file_subscriber = tempfile.TemporaryFile(mode='w+t')

    # Manager is a shared memory section where both processes can access.
    # return_code is a list of two elements where the different processes
    # (publisher and subscriber applications) copy their ReturnCode.
    # These ReturnCodes are identified by the index within the list,
    # every index identifies one application. Therefore, only one application
    # must modifies one element of the list.
    # Once both processes are finished, the list contains the ReturnCode
    # in the corresponding index. This index is set manually and we need it
    # in order to use it later.
    # Example:
    #   Processes:
    #     - Publisher Process (produced_code_index = 1)
    #     - Subscriber Process (produced_code_index = 0)
    #   Code contains:
    #     - return_code[1] contains Publisher Application ReturnCode
    #     - return_code[0] contains Subscriber Application ReturnCode
    publisher_index = 1
    subscriber_index = 0

    log_message('Assigning tasks to processes', verbosity)
    pub = Process(target=run_publisher_shape_main,
                    kwargs={
                        'name_executable':name_executable_pub,
                        'parameters':param_pub,
                        'test_name':test_case.name,
                        'produced_code':return_code,
                        'produced_code_index':publisher_index,
                        'samples_sent':data,
                        'verbosity':verbosity,
                        'timeout':timeout,
                        'file':file_publisher,
                        'subscriber_finished':subscriber_finished,
                        'publisher_finished':publisher_finished
                    })
    sub = Process(target=run_subscriber_shape_main,
                    kwargs={
                        'name_executable':name_executable_sub,
                        'parameters':param_sub,
                        'test_name':test_case.name,
                        'produced_code':return_code,
                        'produced_code_index':subscriber_index,
                        'samples_sent':data,
                        'verbosity':verbosity,
                        'timeout':timeout,
                        'file':file_subscriber,
                        'subscriber_finished':subscriber_finished,
                        'publisher_finished':publisher_finished
                    })

    log_message('Running Subscriber process', verbosity)
    sub.start()
    log_message('Running Publisher process', verbosity)
    pub.start()
    # Wait until these processes finish
    sub.join()
    pub.join()

    log_message('Reading information from temporary files', verbosity)
    file_publisher.seek(0)
    file_subscriber.seek(0)
    information_publisher = file_publisher.read()
    information_subscriber = file_subscriber.read()

    test_case.param_pub = param_pub
    test_case.param_sub = param_sub

    # code[1] contains shape_main publisher application ReturnCode
    # and code[0] the shape_main subscriber application ReturnCode.
    if expected_code_pub == return_code[publisher_index] and expected_code_sub == return_code[subscriber_index]:
        print (f'{test_case.name} : Ok')

    else:
        print(f'Error in : {test_case.name}')
        print(f'Publisher expected code: {expected_code_pub}; \
                Code found: {return_code[publisher_index].name}')
        print(f'Subscriber expected code: {expected_code_sub}; \
                Code found: {return_code[subscriber_index].name}')
        log_message(f'\nInformation about the Publisher:\n \
                      {information_publisher} \
                      \nInformation about the Subscriber:\n \
                      {information_subscriber}', verbosity)

        additional_info_pub = information_publisher.replace('\n', '<br>')
        additional_info_sub = information_subscriber.replace('\n', '<br>')
        test_case.result = [Failure(f'<table> \
                                    <tr> \
                                        <th/>  \
                                        <th>Expected Code</th> \
                                        <th>Code Produced</th> \
                                    </tr> \
                                    <tr> \
                                        <th>Publisher</th> \
                                        <th>{expected_code_pub.name}</th> \
                                        <th>{return_code[publisher_index].name}</th> \
                                    </tr> \
                                    <tr> \
                                        <th>Subscriber</th> \
                                        <th>{expected_code_sub.name}</th> \
                                        <th>{return_code[subscriber_index].name}</th> \
                                    </tr> \
                                </table> \
                               <strong> Information Publisher: </strong> \
                                 <br> {additional_info_pub} <br> \
                               <strong> Information Subscriber: </strong> \
                                 <br> {additional_info_sub}')]

    file_publisher.close()
    file_subscriber.close()


def run_test_pub_pub_sub(
        name_executable_pub: str,
        name_executable_sub: str,
        test_case: TestCase,
        param_pub1: str,
        param_pub2: str,
        param_sub: str,
        expected_code_pub1: ReturnCode,
        expected_code_pub2: ReturnCode,
        expected_code_sub: ReturnCode,
        verbosity: bool,
        timeout: int):

    """ Run two Publisher and one Subscriber and check the ReturnCode

        name_executable_pub <<in>>: name of the shape_main application to run
                as a Publisher
        name_executable_sub <<in>>: name of the shape_main application to run
                as a Subscriber
        test_case <<inout>>: testCase object to test
        param_pub1 <<in>>: shape_main application publisher 1 parameter list
        param_pub2 <<in>>: shape_main application publisher 2 parameter list
        param_sub <<in>>: shape_main application subscriber parameter list
        expected_code_pub1 <<in>>: ReturnCode the Publisher 1 would obtain
                in a non error situation
        expected_code_pub2 <<in>>: ReturnCode the Publisher 2 would obtain
                in a non error situation
        expected_code_sub <<in>>: ReturnCode the Subscriber would obtain
                in a non error situation
        verbosity <<in>>: print debug information
        timeout <<in>>: time pexpect waits until it matches a pattern

        This function runs three different processes: two publisher
        applications and one subscriber application.
        Then it checks that the code obtained is the expected one.
    """
    log_message(f'run_test parameters: \
                    name_executable_pub: {name_executable_pub} \
                    name_executable_sub: {name_executable_sub} \
                    test_case: {test_case.name} \
                    param_pub1: {param_pub1} \
                    param_pub2: {param_pub2} \
                    param_sub: {param_sub} \
                    expected_code_pub1: {expected_code_pub1} \
                    expected_code_pub2: {expected_code_pub2} \
                    expected_code_sub: {expected_code_sub} \
                    verbosity: {verbosity} \
                    timeout: {timeout}',
                    verbosity)

    manager = Manager()
    # used for storing the obtained ReturnCode
    # (from Publisher 1, Publisher 2 and Subscriber)
    code = manager.list(range(3))
    data = Queue() # used for storing the samples

    subscriber_finished = Event()
    publisher_finished = Event()

    log_message('Creating temporary files', verbosity)
    file_subscriber = tempfile.TemporaryFile(mode='w+t')
    file_publisher1 = tempfile.TemporaryFile(mode='w+t')
    file_publisher2 = tempfile.TemporaryFile(mode='w+t')

    # Manager is a shared memory section where the three processes can access.
    # return_code is a list of three elements where the different processes
    # (publisher 1, publisher 2 and subscriber applications) copy their ReturnCode.
    # These ReturnCodes are identified by the index within the list,
    # every index identifies one application. Therefore, only one application
    # must modifies one element of the list.
    # Once both processes are finished, the list contains the ReturnCode
    # in the corresponding index. This index is set manually and we need it
    # in order to use it later.
    # Example:
    #   Processes:
    #     - Publisher 1 Process (produced_code_index = 1)
    #     - Publisher 2 Process (produced_code_index = 2)
    #     - Subscriber Process (produced_code_index = 0)
    #   Code contains:
    #     - return_code[1] contains Publisher 1 Application ReturnCode
    #     - return_code[2] contains Publisher 2 Application ReturnCode
    #     - return_code[0] contains Subscriber Application ReturnCode
    publisher1_index = 1
    publisher2_index = 2
    subscriber_index = 0
    log_message('Assigning tasks to processes', verbosity)
    if test_case.name == 'Test_Ownership_3':
        pub1 = Process(target=run_publisher_shape_main,
                        kwargs={
                            'name_executable':name_executable_pub,
                            'parameters':param_pub1,
                            'test_name':test_case.name,
                            'produced_code':code,
                            'produced_code_index':publisher1_index,
                            'samples_sent':data,
                            'verbosity':verbosity,
                            'timeout':timeout,
                            'file':file_publisher1,
                            'subscriber_finished':subscriber_finished,
                            'publisher_finished':publisher_finished
                        })
        pub2 = Process(target=run_publisher_shape_main,
                        kwargs={
                            'name_executable':name_executable_pub,
                            'parameters':param_pub2,
                            'test_name':test_case.name,
                            'produced_code':code,
                            'produced_code_index':publisher2_index,
                            'samples_sent':data,
                            'verbosity':verbosity,
                            'timeout':timeout,
                            'file':file_publisher2,
                            'subscriber_finished':subscriber_finished,
                            'publisher_finished':publisher_finished
                        })
        sub = Process(target=run_subscriber_shape_main,
                        kwargs={
                            'name_executable':name_executable_sub,
                            'parameters':param_sub,
                            'test_name':test_case.name,
                            'produced_code':code,
                            'produced_code_index':subscriber_index,
                            'samples_sent':data,
                            'verbosity':verbosity,
                            'timeout':timeout,
                            'file':file_subscriber,
                            'subscriber_finished':subscriber_finished,
                            'publisher_finished':publisher_finished
                        })

    if test_case.name == 'Test_Ownership_4':
        pub1 = Process(target=run_publisher_shape_main,
                        kwargs={
                            'name_executable':name_executable_pub,
                            'parameters':param_pub1,
                            'test_name':test_case.name,
                            'produced_code':code,
                            'produced_code_index':publisher1_index,
                            'samples_sent':Queue(),
                            'verbosity':verbosity,
                            'timeout':timeout,
                            'file':file_publisher1,
                            'subscriber_finished':subscriber_finished,
                            'publisher_finished':publisher_finished
                        })
        pub2 = Process(target=run_publisher_shape_main,
                        kwargs={
                            'name_executable':name_executable_pub,
                            'parameters':param_pub2,
                            'test_name':test_case.name,
                            'produced_code':code,
                            'produced_code_index':publisher2_index,
                            'samples_sent':data,
                            'verbosity':verbosity,
                            'timeout':timeout,
                            'file':file_publisher2,
                            'subscriber_finished':subscriber_finished,
                            'publisher_finished':publisher_finished
                        })
        sub = Process(target=run_subscriber_shape_main,
                        kwargs={
                            'name_executable':name_executable_sub,
                            'parameters':param_sub,
                            'test_name':test_case.name,
                            'produced_code':code,
                            'produced_code_index':subscriber_index,
                            'samples_sent':data,
                            'verbosity':verbosity,
                            'timeout':timeout,
                            'file':file_subscriber,
                            'subscriber_finished':subscriber_finished,
                            'publisher_finished':publisher_finished
                        })

    log_message('Running Subscriber process', verbosity)
    sub.start()
    log_message('Running Publisher 1 process', verbosity)
    pub1.start()
    time.sleep(1) # used to make the two Publishers have different seeds
                  # to generate the samples
    log_message('Running Publisher 2 process', verbosity)
    pub2.start()

    sub.join()
    pub1.join()
    pub2.join()

    log_message('Reading information from temporary files', verbosity)
    file_publisher1.seek(0)
    file_publisher2.seek(0)
    file_subscriber.seek(0)
    information_publisher1 = file_publisher1.read()
    information_publisher2 = file_publisher2.read()
    information_subscriber = file_subscriber.read()

    test_case.param_pub1 = param_pub1
    test_case.param_pub2 = param_pub2
    test_case.param_sub = param_sub

    # code[1] contains shape_main publisher 1 application ReturnCode,
    # code[2] the shape_main publisher 2 application ReturnCode
    # and code[0] the shape_main subscriber application ReturnCode.
    if expected_code_pub1 ==  code[publisher1_index] and expected_code_sub == code[subscriber_index] \
        and expected_code_pub2 == code[publisher2_index]:
        print (f'{test_case.name} : Ok')

    else:
        print(f'Error in : {test_case.name}')
        print(f'Publisher 1 expected code: {expected_code_pub1}; \
                Code found: {code[publisher1_index].name}')
        print(f'Publisher 2 expected code: {expected_code_pub2}; \
                Code found: {code[publisher2_index].name}')
        print(f'Subscriber expected code: {expected_code_sub}; \
                Code found: {code[subscriber_index].name}')
        log_message(f'\nInformation about the Publisher 1:\n \
                      {information_publisher1} \
                      \nInformation about the Publisher 2:\n \
                      {information_publisher2} \
                      \nInformation about the Subscriber:\n \
                      {information_subscriber}', verbosity)

        additional_info_pub1 = information_publisher1.replace('\n', '<br>')
        additional_info_pub2 = information_publisher2.replace('\n', '<br>')
        additional_info_sub = information_subscriber.replace('\n', '<br>')

        test_case.result = [Failure(f'<table> \
                                    <tr> \
                                        <th/> \
                                        <th>Expected Code</th> \
                                        <th>Code Produced</th> \
                                    </tr> \
                                    <tr> \
                                        <th>Publisher 1</th> \
                                        <th>{expected_code_pub1.name}</th> \
                                        <th>{code[publisher1_index].name}</th> \
                                    </tr> \
                                    <tr> \
                                        <th>Publisher 2</th> \
                                        <th>{expected_code_pub2.name}</th> \
                                        <th>{code[publisher2_index].name}</th> \
                                    </tr> \
                                    <tr> \
                                        <th>Subscriber</th> \
                                        <th>{expected_code_sub.name}</th> \
                                        <th>{code[subscriber_index].name}</th> \
                                    </tr> \
                                </table> \
                               <strong> Information Publisher 1: </strong> \
                                 <br> {additional_info_pub1} <br> \
                               <strong> Information Publisher 2: </strong> \
                                 <br> {additional_info_pub2} <br> \
                               <strong> Information Subscriber: </strong> \
                                 <br> {additional_info_sub}')]

    file_subscriber.close()
    file_publisher1.close()
    file_publisher2.close()

class Arguments:
    def parser():
        parser = argparse.ArgumentParser(
            description='Interoperability Test',
            add_help=True)

        gen_opts = parser.add_argument_group(title='general options')
        gen_opts.add_argument('-P', '--publisher',
            default=None,
            required=True,
            type=str,
            metavar='publisher_name',
            help='Publisher Shape Application')
        gen_opts.add_argument('-S', '--subscriber',
            default=None,
            required=True,
            type=str,
            metavar='subscriber_name',
            help='Subscriber Shape Application')

        optional = parser.add_argument_group(title='optional parameters')
        optional.add_argument('-v','--verbose',
            default=False,
            required=False,
            action='store_true',
            help='Print more information to stdout.')

        out_opts = parser.add_argument_group(title='output options')
        out_opts.add_argument('-f', '--output-format',
            default='junit',
            required=False,
            type=str,
            choices=['junit', 'csv', 'xlxs'],
            help='Output format.')
        out_opts.add_argument('-o', '--output-name',
            required=False,
            metavar='filename',
            type=str,
            help='Report filename.')

        return parser

def main():

    parser = Arguments.parser()
    args = parser.parse_args()

    options = {
        'publisher': args.publisher,
        'subscriber': args.subscriber,
        'verbosity': args.verbose,
    }
    # The executables's names are supposed to follow the pattern: name_shape_main
    # We will keep only the part of the name that is useful, deleting the path and
    # the substring _shape_main.
    # Example: if the shape_main application's name (including the path) is:
    #  ./srcCxx/objs/x64Linux4gcc7.3.0/rti_connext_dds-6.1.1_shape_main_linux
    # we will take the substring rti_connext_dds-6.1.1.
    # That will be the name that will appear in the report.
    name_publisher = (options['publisher'].split('_shape')[0]).split('/')[-1]
    name_subscriber = (options['subscriber'].split('_shape')[0]).split('/')[-1]

    if args.output_format is None:
        options['output_format'] = 'junit'
    else:
        options['output_format'] = args.output_format
    if args.output_name is None:
        now = datetime.now()
        date_time = now.strftime('%Y%m%d-%H_%M_%S')
        options['filename_report'] = name_publisher+'-'+name_subscriber \
                                    +'-'+date_time+'.xml'
        xml = JUnitXml()

    else:
        options['filename_report'] = args.output_name
        file_exists = exists(options['filename_report'])
        if file_exists:
            xml = JUnitXml.fromfile(options['filename_report'])
        else:
            xml = JUnitXml()

    # TestSuite is a class from junitparser that will contain the
    # results of running different TestCases between two shape_main
    # applications. A TestSuite contains a collection of TestCases.
    suite = TestSuite(f"{name_publisher}---{name_subscriber}")
    TestCase.param_pub = Attr('Parameters_Publisher')
    TestCase.param_sub = Attr('Parameters_Subscriber')
    TestCase.param_pub1 = Attr('Parameters_Publisher_1')
    TestCase.param_pub2 = Attr('Parameters_Publisher_2')

    timeout = 10
    now = datetime.now()
    for k, v in rtps_test_suite_1.items():
        # TestCase is an class from junitparser whose attributes
        # are: name and result (OK, Failure, Error and Skipped),
        # apart from other custom attributes (in this case param_pub,
        # param_sub, param_pub1 and param_pub2).
        case = TestCase(f'{k}')
        now_test_case = datetime.now()
        if k == 'Test_Ownership_3' or k == 'Test_Ownership_4':
            run_test_pub_pub_sub(name_executable_pub=options['publisher'],
                                 name_executable_sub=options['subscriber'],
                                 test_case=case,
                                 param_pub1=v[0],
                                 param_pub2=v[1],
                                 param_sub=v[2],
                                 expected_code_pub1=v[3],
                                 expected_code_pub2=v[4],
                                 expected_code_sub=v[5],
                                 verbosity=options['verbosity'],
                                 timeout=timeout
            )

        else:
            run_test(name_executable_pub=options['publisher'],
                     name_executable_sub=options['subscriber'],
                     test_case=case,
                     param_pub=v[0],
                     param_sub=v[1],
                     expected_code_pub=v[2],
                     expected_code_sub=v[3],
                     verbosity=options['verbosity'],
                     timeout=timeout
            )
        case.time = (datetime.now() - now_test_case).total_seconds()
        suite.add_testcase(case)

    suite.time = (datetime.now() - now).total_seconds()
    xml.add_testsuite(suite)

    xml.write(options['filename_report'])

if __name__ == '__main__':
    main()
