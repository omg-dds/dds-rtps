from enum import Enum

class ReturnCode(Enum):
    """"
    Codes to give information about Shape Applications' behavior.

    OK                   : Publisher/Subscriber sent/received data correctly
    UNRECOGNIZED_VALUE   : Parameters for the Publisher/Subscriber not supported
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
    UNRECOGNIZED_VALUE = 1
    TOPIC_NOT_CREATED = 2
    READER_NOT_CREATED = 3
    WRITER_NOT_CREATED = 4
    FILTER_NOT_CREATED = 5
    INCOMPATIBLE_QOS = 6
    READER_NOT_MATCHED = 7
    WRITER_NOT_MATCHED = 8
    WRITER_NOT_ALIVE = 9
    DATA_NOT_RECEIVED = 10
    DATA_NOT_SENT = 11
    DATA_NOT_CORRECT = 12
    RECEIVING_FROM_ONE = 13
    RECEIVING_FROM_BOTH = 14
