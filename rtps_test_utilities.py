#################################################################
# Use and redistribution is source and binary forms is permitted
# subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
# at the following URL:
#
# https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
#
#################################################################

from enum import Enum
class ReturnCode(Enum):
    """"
    Codes to give information about Shape Applications' behavior.

    OK                   : Publisher/Subscriber sent/received data correctly
    TOPIC_NOT_CREATED    : Publisher/Subscriber does not create the topic
    READER_NOT_CREATED   : Subscriber does not create the Data Reader
    WRITER_NOT_CREATED   : Publisher does not create the Data Writer
    FILTER_NOT_CREATED   : Subscriber does not create the content filter
    INCOMPATIBLE_QOS     : Publisher/Subscriber with incompatible QoS.
    READER_NOT_MATCHED   : Publisher does not find any compatible Data Reader
    WRITER_NOT_MATCHED   : Subscriber does not find any compatible Data Writer
    WRITER_NOT_ALIVE     : Subscriber does not find any live Data Writer
    DATA_NOT_RECEIVED    : Subscriber does not receive the data
    DATA_NOT_SENT        : Publisher does not send the data
    DATA_NOT_CORRECT     : Subscriber does not find the data expected
    RECEIVING_FROM_ONE   : Subscriber receives from one Publisher
    RECEIVING_FROM_BOTH  : Subscriber receives from two Publishers
    """
    OK = 0
    TOPIC_NOT_CREATED = 1
    READER_NOT_CREATED = 2
    WRITER_NOT_CREATED = 3
    FILTER_NOT_CREATED = 4
    INCOMPATIBLE_QOS = 5
    READER_NOT_MATCHED = 6
    WRITER_NOT_MATCHED = 7
    WRITER_NOT_ALIVE = 8
    DATA_NOT_RECEIVED = 9
    DATA_NOT_SENT = 10
    DATA_NOT_CORRECT = 11
    RECEIVING_FROM_ONE = 12
    RECEIVING_FROM_BOTH = 13

def log_message(message, verbosity):
    if verbosity:
        print(message)

def no_check(child_sub, samples_sent, timeout):
    return ReturnCode.OK
