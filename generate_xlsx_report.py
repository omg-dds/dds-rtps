#!/usr/bin/python
#################################################################
# Use and redistribution is source and binary forms is permitted
# subject to the OMG-DDS INTEROPERABILITY TESTING LICENSE found
# at the following URL:
#
# https://github.com/omg-dds/dds-rtps/blob/master/LICENSE.md
#
#################################################################

import argparse
import junitparser
import lxml
import pathlib
import xlsxwriter
import sys
import os
import re
import datetime
from rtps_test_utilities import log_message
import test_suite
from enum import Enum

class TestStatus(Enum):
    """
    Enumeration of the test status.
    PASSED: The test has passed
    FAILED: The test has failed
    PUB_UNSUPPORTED: The test is unsupported for the Publisher
    SUB_UNSUPPORTED: The test is unsupported for the Subscriber
    PUB_SUB_UNSUPPORTED: The test is unsupported for both Publisher and Subscriber
    """
    PASSED = 1
    FAILED = 2
    PUB_UNSUPPORTED = 3
    SUB_UNSUPPORTED = 4
    PUB_SUB_UNSUPPORTED = 5

class XlxsReportArgumentParser:
    """Class that parse the arguments of the application."""
    def argument_parser():
        parser = argparse.ArgumentParser(
            description='Creation of an xlsx report of interoperability of products compliant '
                'with OMG DDS-RTPS standard. This script generates automatically '
                'the verification between two shape_main executables. '
                'It also generates an XML report in JUnit format.',
            add_help=True)

        gen_opts = parser.add_argument_group(title='general options')
        gen_opts.add_argument('-o', '--output',
            default=None,
            required=True,
            type=str,
            metavar='output',
            help='Path to the output file. It should have an xlsx file extension')
        gen_opts.add_argument('-i', '--input',
            default=None,
            required=True,
            type=str,
            metavar='input',
            help='Path to the input file. It should have an xml file extension')

        return parser


class ProductUtils:
    @staticmethod
    def get_company_name(product:str) -> str:
        """Returns the company name"""
        if 'connext' in product.lower():
            return 'Real-Time Innovations (RTI)'
        elif 'opendds' in product.lower():
            return 'OpenDDS Foundation'
        elif 'coredx' in product.lower():
            return 'Twin Oaks Computing, Inc'
        elif 'intercom' in product.lower():
            return 'Kongsberg'
        elif 'fastdds' in product.lower():
            return 'eProsima'
        elif 'dust' in product.lower():
            return 'S2E Software Systems'
        else:
            raise RuntimeError('Impossible to get company name: ' + product)

    @staticmethod
    def get_product_name(product:str) -> str:
        """Returns a beautified product name and version"""
        # set the beautified name and version
        if 'connext' in product.lower() and 'micro' in product.lower():
            return 'Connext DDS Micro ' + re.search(r'([\d.]+)', product).group(1)
        if 'connext' in product.lower():
            return 'Connext DDS ' + re.search(r'([\d.]+)', product).group(1)
        elif 'opendds' in product.lower():
            return 'OpenDDS ' + re.search(r'([\d.]+)', product).group(1)
        elif 'coredx' in product.lower():
            return 'CoreDX DDS ' + re.search(r'([\d.]+)', product).group(1)
        elif 'intercom' in product.lower():
            return 'InterCOM DDS ' + re.search(r'([\d.]+)', product).group(1)
        elif 'fastdds' in product.lower():
            return 'FastDDS ' + re.search(r'([\d.]+)', product).group(1)
        elif 'dust_dds' in product.lower():
            return 'Dust DDS ' + re.search(r'([\d.]+)', product).group(1)
        else:
            raise RuntimeError('Impossible to get product name: ' + product)


class JunitAggregatedData:
    """
    Class that contains the JUnit aggregated data as a tuple of 3 integers
    [tests_passed, total_tests, tests_unsupported]. This identifies one cell in
    the summary table that shows the product and the amount of tests passed,
    total and unsupported.
    """
    data: tuple[int,int, int] # [tests_passed, total_tests, tests_unsupported]

    def __init__(self, passed_tests: int, total_tests: int, unsupported_tests: int) -> None:
        self.data = [passed_tests, total_tests, unsupported_tests]

    def get_passed_tests(self):
        return self.data[0]

    def get_total_tests(self):
        return self.data[1]

    def get_unsupported_tests(self):
        return self.data[2]

    def get_supported_tests(self):
        return self.data[1] - self.data[2]

    def __str__(self) -> str:
        return f'({self.data[0]}, {self.data[1]}, {self.data[2]})'

class JunitTestCaseAggregatedData:
    """
    Class that contains the JUnit aggregated data per test case. The table
    generated from this class shows the tests passed per product (as
    Publisher or Subscriber) and with all other products (as Subscribers or
    Publishers, the opposite).
    This tuple is composed by 2 strings that identifies the other product
    (Publisher or Subscriber), the test name and the status of the test.
    """
    # [publisher or subscriber name, test_name, status]
    data: tuple[str,str,TestStatus] = None

    def __init__(self, product: str, test_name: str, status: TestStatus) -> None:
        self.data = (product, test_name, status)

    def get_product_name(self):
        return self.data[0]

    def get_test_name(self):
        return self.data[1]

    def get_status(self):
        return self.data[2]

    def __str__(self) -> str:
        return f'{self.data}'

class JunitData:
    """
    This class represents all extracted data from the JUnit results. This is the
    data that will be represented in the xlsx document.
    summary_dict: dictionary that contains the passed_tests/total_tests per
                  product(key)
    product_summary_dict: dictionary that contains the passed_tests/total_tests
                          information per pair of products (key). For example
                          RTI Connext/OpenDDS --> passed_tests/total_tests
    publisher_product_dict: dictionary that contains a list with all results of
                            all tests for a specific publisher product (key)
                            with all other products as subscriber.
    subscriber_product_dict: dictionary that contains a list with all results of
                             all tests for a specific publisher product (key)
                             with all other products as subscriber.
    """
    # [product, aggregated data]
    summary_dict: dict[str,JunitAggregatedData] = {}
    # [(publisher_name, subscriber_name), aggregated data]
    product_summary_dict: dict[(str,str),JunitAggregatedData] = {}

    # [publisher_name, list of test case aggregated data]
    publisher_product_dict: dict[str,list[JunitTestCaseAggregatedData]] = {}
    # [subscriber_name, list of test case aggregated data]
    subscriber_product_dict: dict[str,list[JunitTestCaseAggregatedData]] = {}

    def __init__(self, input: pathlib.Path):
        self.get_info(input)

    @staticmethod
    def xml_parser(file):
        """Function to parse the XML file"""

        parser = lxml.etree.XMLParser(huge_tree=True)
        return lxml.etree.parse(file, parser)

    def update_value_aggregated_data_dict(self,
            dictionary: dict,
            key: str,
            value: JunitAggregatedData) -> None:
        """
        Update the value of the 'key' in the 'dictionary'. If the key
        doesn't exist, add the new value to the dictionary, otherwise,
        add the numbers from 'value' to the current dictionary value.
        """
        if key in dictionary:
            updated_data = JunitAggregatedData(
                dictionary[key].get_passed_tests() + value.get_passed_tests(),
                dictionary[key].get_total_tests() + value.get_total_tests(),
                dictionary[key].get_unsupported_tests() + value.get_unsupported_tests()
            )
            dictionary[key] = updated_data
        else:
            dictionary[key] = value

    def update_value_to_product_dict(self,
            key: str,
            product_dict: dict[str,list[JunitTestCaseAggregatedData]],
            value: JunitTestCaseAggregatedData) -> None:
        """
        Update the value of the 'key' in the 'product_dict'. If the key
        doesn't exist, add the new value to the dictionary (as a list of 1
        elements), otherwise, add the element from 'value' to the current
        dictionary value (list).
        """
        if key in product_dict:
            product_dict[key].append(value)
        else:
            product_dict[key] = [value]

    def get_info(self, input: pathlib.Path = None):
        """
        Get the information from the JUnit XML file and store it in the
        the corresponding fields of this class.
        """
        # get the DOM of the XML
        xml = junitparser.JUnitXml.fromfile(input, parse_func=self.xml_parser)

        # for every test suite in the XML
        for suite in list(iter(xml)):
            # get beautified publisher and subscriber names from the test suite
            # name
            product_names = re.search(r'([\S]+)\-\-\-([\S]+)', suite.name)
            publisher_name = ProductUtils.get_product_name(product_names.group(1))
            subscriber_name = ProductUtils.get_product_name(product_names.group(2))

            # for each test case in the test suite, fill out the dictionaries
            # that contains information about the product as publisher and
            # subscriber
            unsupported_tests_count = 0
            for case in list(iter(suite)):
                is_pub_unsupported = False
                is_sub_unsupported = False
                status = None
                test_name = re.search(r'((?:Test_)[\S]+_\d+)', case.name).group(1)

                # count number of unsupported tests for the summary
                # result array is not empty and the message contains 'UNSUPPORTED_FEATURE'
                if case.result and len(case.result) > 0:
                    if 'PUB_UNSUPPORTED_FEATURE' in case.result[0].message.upper():
                        is_pub_unsupported = True
                    if 'SUB_UNSUPPORTED_FEATURE' in case.result[0].message.upper():
                        is_sub_unsupported = True

                if is_pub_unsupported or is_sub_unsupported:
                    unsupported_tests_count += 1

                # Get test status
                if case.is_passed:
                    status = TestStatus.PASSED
                elif is_pub_unsupported and is_sub_unsupported:
                    status = TestStatus.PUB_SUB_UNSUPPORTED
                elif is_pub_unsupported:
                    status = TestStatus.PUB_UNSUPPORTED
                elif is_sub_unsupported:
                    status = TestStatus.SUB_UNSUPPORTED
                else:
                    status = TestStatus.FAILED


                # update the value of the publisher_name as publisher with
                # all products as subscribers.
                # the tuple is (subscriber_name, test_name, status)
                publisher_test_result = JunitTestCaseAggregatedData(
                    product=subscriber_name,
                    test_name=test_name,
                    status=status
                )

                # add the resulting tuple to the publisher dictionary, the key
                # is the publisher_name because it will be the publisher table
                # against all product as subscribers
                self.update_value_to_product_dict(
                        key=publisher_name,
                        value=publisher_test_result,
                        product_dict=self.publisher_product_dict
                )

                # update the value of the subscriber_name as subscriber with
                # all products as publishers.
                # the tuple is (publisher_name, test_name, status)
                subscriber_test_result = JunitTestCaseAggregatedData(
                    product=publisher_name,
                    test_name=test_name,
                    status=status
                )

                # add the resulting tuple to the subscriber dictionary, the key
                # is the subscriber_name because it will be the subscriber table
                # against all product as publishers
                self.update_value_to_product_dict(
                        key=subscriber_name,
                        value=subscriber_test_result,
                        product_dict=self.subscriber_product_dict
                )

            # get the value of the passed_tests, total_tests and
            # unsupported_tests as a JunitAggregatedData
            element = JunitAggregatedData(
                suite.tests - suite.failures - suite.skipped - suite.errors,
                suite.tests,
                unsupported_tests_count
            )

            # update the information of the product in the summary_dict with
            # the information of the publisher and the subscriber
            self.update_value_aggregated_data_dict(
                self.summary_dict, publisher_name, element)
            # do not add duplicated data if the publisher and subscriber names
            # are the same
            if publisher_name != subscriber_name:
                self.update_value_aggregated_data_dict(
                    self.summary_dict, subscriber_name, element)

            # Get table with the summary of the test
            # passed/total_tests/unsupported_tests for every product as
            # publisher and as subscriber
            product_dict_key = (publisher_name, subscriber_name)
            product_test_data = JunitAggregatedData(
                suite.tests - suite.failures - suite.skipped - suite.errors,
                suite.tests,
                unsupported_tests_count)
            self.update_value_aggregated_data_dict(
                self.product_summary_dict,
                product_dict_key,
                product_test_data)

class ColorUtils:
    """Set specific colors"""
    GREEN = '#4EB168'
    LIME = '#86A336'
    YELLOW ='#B58F19'
    ORANGE = '#DB722e'
    RED = '#F2505A'

class XlsxReport:
    """
    This class creates a workbook that shows the following information in
    its worksheets:
        * Summary: two tables that contain:
        * passed_tests/total_tests for every product
        * passed_tests/total_tests for every product as publisher and subscriber
        * One worksheet per product that shows the test results as publisher
        and as subscriber
    The parameters of this class are:
        * workbook: the workbook created by xlsxwriter
        * __data: private member that contains the data represented in the
                workbook
        * __formats: private member that contains the formats of the workbook
    """
    workbook: xlsxwriter.Workbook
    __data: JunitData
    __formats: dict = {} # contains the format name and formats objects
    REPO_LINK = 'https://github.com/omg-dds/dds-rtps'
    REPO_DOC = 'https://omg-dds.github.io/dds-rtps/'

    def __init__(self, output: pathlib.Path, data: JunitData):
        """
        Initializer that receives the JunitData and the output file. This
        adds the formats used to the workbook and the different worksheets
        """
        self.workbook = xlsxwriter.Workbook(output)
        # set the default workbook size
        self.workbook.set_size(2000,1500)
        self.__data = data
        self.add_formats()
        self.create_summary_worksheet()
        self.create_description_worksheet()
        self.add_data_test_worksheet()
        self.workbook.close()

    def set_worksheet_defaults(self, worksheet: xlsxwriter.Workbook.worksheet_class):
        # set default values
        worksheet.set_zoom(130)

    def create_summary_worksheet(self, name: str = 'Summary'):
        """
        Creates a summary worksheet, with a header that contains static info
        and a summary of the passed_tests/total_tests.
        """
        summary_worksheet = self.workbook.add_worksheet(name=name)
        self.set_worksheet_defaults(summary_worksheet)
        # The static info of the summary requires 6 rows (row value 5) + 2 gaps
        # rows.
        # The tables leave the first column (value 0) as gap
        self.add_data_summary_worksheet(
            starting_row=9,
            starting_column=1,
            worksheet=summary_worksheet)
        # After having all data that may have an unknown length, we call
        # autofit to modify the column size to show all data, then we add
        # the static data that does not require autofit
        summary_worksheet.autofit()
        self.add_static_data_summary_worksheet(summary_worksheet)

    def create_description_worksheet(self, name: str = 'Test Descriptions'):
        """
        Creates a test description worksheet from test_suite.py.
        """
        description_worksheet = self.workbook.add_worksheet(name=name)
        self.set_worksheet_defaults(description_worksheet)

        # Set the test names and static data before doing the autofit.
        self.add_static_data_description_worksheet(description_worksheet)
        self.add_test_name_description_worksheet(description_worksheet)

        description_worksheet.autofit()

        # Add the title of the test after doing the autofit
        self.add_title_description_worksheet(description_worksheet)

    def add_formats(self):
        """Add the specific format"""
        self.__formats['title'] = self.workbook.add_format({
            'bold': True,
            'font_size': 36,
            'text_wrap': False
        })
        self.__formats['subtitle'] = self.workbook.add_format({
            'font_size': 26
        })

        self.__formats['product_title'] = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16,
            'text_wrap': False
        })
        self.__formats['product_subtitle'] = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter'
        })

        self.__formats['bold'] = self.workbook.add_format(properties={'bold': True})

        self.__formats['bold_w_border'] = self.workbook.add_format(
            properties={'bold': True, 'border': 1})

        self.__formats['result_green'] = value_format = self.workbook.add_format(
            properties={'bg_color': ColorUtils.GREEN,
                        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        self.__formats['result_lime'] = value_format = self.workbook.add_format(
            properties={'bg_color': ColorUtils.LIME,
                        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        self.__formats['result_yellow'] = value_format = self.workbook.add_format(
            properties={'bg_color': ColorUtils.YELLOW,
                        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        self.__formats['result_orange'] = value_format = self.workbook.add_format(
            properties={'bg_color': ColorUtils.ORANGE,
                        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        self.__formats['result_red'] = value_format = self.workbook.add_format(
            properties={'bg_color': ColorUtils.RED,
                        'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})

    def get_format_color(self, index: int, num_elements: int):
        """
        Return the corresponding color format depending on the ratio of
        passed_tests/total_tests
        """
        # this might only happen for supported tests when the total supported
        # scenarios is 0
        if num_elements == 0:
            return self.__formats['result_red']

        ratio = index / num_elements

        if ratio < 0.25:
            return self.__formats['result_red']
        elif ratio < 0.5:
            return self.__formats['result_orange']
        elif ratio < 0.75:
            return self.__formats['result_yellow']
        elif ratio < 1:
            return self.__formats['result_lime']
        else: # ratio == 1
            return self.__formats['result_green']

    def get_format_color_test_status(self, status: TestStatus):
        """
        Get the corresponding color format depending on 'status'.
        Green if status is PASSED, Red if FAILED, Yellow if UNSUPPORTED
        """
        if status == TestStatus.PASSED:
            # Return GREEN
            return self.__formats['result_green']
        elif status == TestStatus.FAILED:
            # Return RED
            return self.__formats['result_red']
        else:
            # Return YELLOW
            return self.__formats['result_yellow']

    def add_static_data_test(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            product_name: str,
            pub_product_count: int,
            sub_product_count) -> (int, int):
        """Add static data to the specific product worksheet"""

        if sub_product_count > 0:
            # the last column of the publisher table is
            # `2 (column C) + product_count - 1`
            # the -1 is because the column C is already counted
            last_column_publisher = 1 + sub_product_count
            if last_column_publisher > 2:
                worksheet.merge_range(
                    # row 1, from column C till last_column_publisher
                    0, 2, 0, last_column_publisher,
                    'Publisher: ' + product_name,
                    self.__formats['product_title'])
                worksheet.merge_range(
                    # row 2, from column C till last_column_publisher
                    1, 2, 1, last_column_publisher,
                    'Subscriber (next row): ',
                    self.__formats['product_title'])
            else:
                worksheet.write(
                    # row 1, column C
                    0, 2,
                    'Publisher: ' + product_name,
                    self.__formats['product_title'])
                worksheet.write(
                    # row 2, column C
                    1, 2,
                    'Subscriber (next row): ',
                    self.__formats['product_title'])

        if pub_product_count > 0:
            # the subscriber table starts at last_column_publisher + 1
            # the +1 is the gap between the publisher and subscriber tables
            last_column_subscriber = last_column_publisher + 1 + pub_product_count
            if last_column_subscriber > last_column_publisher + 2:
                worksheet.merge_range(
                    # row 1, from column last_column_publisher + 2 till last_column_subscriber
                    # +2 = next_column + gap_between_tables
                    0, last_column_publisher + 2, 0, last_column_subscriber,
                    'Subscriber: ' + product_name,
                    self.__formats['product_title'])
                worksheet.merge_range(
                    # row 2, from column last_column_publisher + 2 till last_column_subscriber
                    # +2 = next_column + gap_between_tables
                    1, last_column_publisher + 2, 1, last_column_subscriber,
                    'Publisher (next row): ',
                    self.__formats['product_title'])
            else:
                worksheet.write(
                    # row 1, column last_column_publisher + 2
                    # +2 = next_column + gap_between_tables
                    0, last_column_publisher + 2,
                    'Subscriber: ' + product_name,
                    self.__formats['product_title'])
                worksheet.write(
                    # row 2, column last_column_publisher + 2
                    # +2 = next_column + gap_between_tables
                    1, last_column_publisher + 2,
                    'Publisher (next row): ',
                    self.__formats['product_title'])

        return (1, last_column_subscriber)

    def add_data_test_worksheet(self):
        """
        Adds test data to the product worksheet, this includes all tests for
        a product as publisher and all products as subscribers. And also,
        a product as subscriber and all other products as publishers.
        """
        # create a list that contains the worksheet names per product. These
        # product names are the same for the publisher and the subscriber
        pub_product_names = []
        for name in self.__data.publisher_product_dict.keys():
            pub_product_names.append(name)

        sub_product_names = []
        for name in self.__data.subscriber_product_dict.keys():
            sub_product_names.append(name)

        # Create a worksheet per product that contains the following info for
        # all tests:
        #  * product as publisher with all other products as subscribers
        #  * product as subscriber with all other products as publishers
        for name in pub_product_names:
            # truncate the name of the string to 31 chars
            worksheet = self.workbook.add_worksheet((name)[:31])
            self.set_worksheet_defaults(worksheet)

            current_cell = (1, 1) # B2

            # next row
            starting_row = current_cell[0] + 1

            # Add table with the product as publisher
            current_cell = self.add_product_table(
                worksheet=worksheet,
                starting_column=1, # B
                starting_row=starting_row,
                value=self.__data.publisher_product_dict[name],
                print_test_name=True
            )

            # Set the column size of the separation column between publisher
            # and subscriber tables
            worksheet.set_column(current_cell[1] + 1, current_cell[1] + 1, 4)

            # Add table with the product as subscriber

            # as the test_name is not printed, the starting_column does not
            # write anything, so, the table starts at starting_column + 1
            if name in sub_product_names:
                self.add_product_table(
                    worksheet=worksheet,
                    starting_column=current_cell[1] + 1, # next column
                    starting_row=starting_row,
                    value=self.__data.subscriber_product_dict[name],
                    print_test_name=False
                )

            # After having all data that may have an unknown length, we call
            # autofit to modify the column size to show all data, then we add
            # the static data that does not require autofit
            worksheet.autofit()
            self.add_static_data_test(
                    worksheet=worksheet,
                    product_name=name,
                    pub_product_count=len(pub_product_names),
                    sub_product_count=len(sub_product_names))


    def add_product_table(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            starting_row: int,
            starting_column: int,
            value: list[JunitTestCaseAggregatedData],
            print_test_name: bool):
        """
        This function adds the test results for one specific publisher with
        all products as subscribers and one specific subscriber with all
        products as publishers to the worksheet.
        """

        current_column = starting_column
        current_row = starting_row
        subscriber_row = starting_row
        test_column = starting_column

        # The starting cell is the title of the test column
        if print_test_name:
            worksheet.write(starting_row, starting_column,
                'Test',
                self.__formats['bold_w_border'])

        # This column dictionary will keep the column for the subscriber product
        column_dict = {}
        row_dict = {}
        # for all elements (test results), add the corresponding value to the
        # worksheet
        for element in value:
            if element.get_product_name() in column_dict:
                # if the product has been added before, just set the
                # process_column to the right column number.
                process_column = column_dict[element.get_product_name()]
            else:
                # if the product hasn't been added before, add the tag to
                # the corresponding column and set the process_column to the
                # column where the result will be saved
                current_column += 1
                process_column = current_column
                column_dict[element.get_product_name()] = current_column
                worksheet.write(
                        subscriber_row,
                        current_column,
                        element.get_product_name(),
                        self.__formats['bold_w_border'])

            if element.get_test_name() in row_dict:
                # if the test has been added before, just set the
                # process_row to the right row number.
                process_row = row_dict[element.get_test_name()]
            else:
                # if the test hasn't been added before, add the tag to
                # the corresponding row and set the process_row to the row
                # where the result will be saved
                current_row += 1
                process_row = current_row
                row_dict[element.get_test_name()] = current_row
                if print_test_name:
                    worksheet.write(
                            current_row,
                            test_column,
                            element.get_test_name(),
                            self.__formats['bold_w_border'])

            # get status string of the test result
            if element.get_status() == TestStatus.PASSED:
                str_result = 'OK'
            elif element.get_status() == TestStatus.FAILED:
                str_result = 'ERROR'
            elif element.get_status() == TestStatus.PUB_UNSUPPORTED:
                str_result = 'PUB UNSUPPORTED'
            elif element.get_status() == TestStatus.SUB_UNSUPPORTED:
                str_result = 'SUB UNSUPPORTED'
            elif element.get_status() == TestStatus.PUB_SUB_UNSUPPORTED:
                str_result = 'PUB/SUB UNSUPPORTED'
            else:
                str_result = 'UNKNOWN'

            # write status string to the test result
            worksheet.write(
                    process_row,
                    process_column,
                    str_result,
                    self.get_format_color_test_status(element.get_status()))
        return (current_row, current_column)

    def add_data_summary_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            starting_row: int,
            starting_column: int):
        """
        This function adds the table passed_tests/total_tests per product and
        another table with passed_tests/total_tests with all products as
        publishers/subscribers.
        """
        current_row = starting_row
        current_column = starting_column
        worksheet.write(
            current_row, current_column,
            'Company', self.__formats['bold_w_border'])
        worksheet.write(
            current_row, current_column + 1,
            'Product', self.__formats['bold_w_border'])
        worksheet.write(
            current_row, current_column + 2,
            'Tests Passed', self.__formats['bold_w_border'])
        worksheet.write(
            current_row, current_column + 3,
            'Supported Tests', self.__formats['bold_w_border'])
        worksheet.write(
            current_row, current_column + 4,
            'Supported Tests Passed', self.__formats['bold_w_border'])

        current_row += 1

        # Create table with the total passed_tests/total_tests per product
        for product_name, value in self.__data.summary_dict.items():
            # company name
            worksheet.write(
                current_row, current_column,
                ProductUtils.get_company_name(product_name),
                self.__formats['bold_w_border'])
            # product name
            worksheet.write(
                current_row, current_column + 1,
                product_name,
                self.__formats['bold_w_border'])
            # test passed
            worksheet.write(
                current_row, current_column + 2,
                str(value.get_passed_tests()) + ' / ' +
                    str(value.get_total_tests()),
                self.get_format_color(value.get_passed_tests(),
                                      value.get_total_tests()))
            # supported tests
            worksheet.write(
                current_row, current_column + 3,
                str(value.get_supported_tests()) + ' / ' +
                    str(value.get_total_tests()),
                self.__formats['result_yellow'] if value.get_unsupported_tests() > 0
                    else self.__formats['result_green'])
            # supported tests passed
            worksheet.write(
                current_row, current_column + 4,
                str(value.get_passed_tests()) + ' / ' +
                    str(value.get_supported_tests()),
                self.get_format_color(value.get_passed_tests(),
                                      value.get_supported_tests()))
            current_row += 1

        # Add 2 rows of gap for the next table
        current_row += 2
        worksheet.write(
            current_row, current_column,
            'Test Result: passed / supported / total', self.__formats['bold_w_border'])
        current_row += 1
        worksheet.write(
            current_row, current_column,
            'Publisher (row)/Subscriber (column)', self.__formats['bold_w_border'])

        # create a dictionary to store the row/column of the product name
        # for example, row_dict['Connext DDS 6.1.2'] = 30 means that the
        # row (publisher) of Connext DDS 6.1.2 is in the xlsx row 29.
        # Column for the publisher is always fixed: 1 --> B
        # Row for the subscriber is always fixed: current_row
        subscriber_row = current_row
        publisher_column = 1
        row_dict={} # publishers
        column_dict={} # subscribers

        # Add the table passed_tests/total_tests with all combinations of product
        # as publishers and as subscribers
        for (publisher_name, subscriber_name), value in self.__data.product_summary_dict.items():
            # if the publisher hasn't been already processed yet, determine
            # what is the process_row by selecting the next free row
            # (current_row+1)
            if not publisher_name in row_dict:
                current_row += 1
                process_row = current_row
                row_dict[publisher_name] = current_row
                worksheet.write(current_row, publisher_column,
                                publisher_name, self.__formats['bold_w_border'])
            else:
                # if the publisher has been already processed, just set the
                # process_row to the corresponding row
                process_row = row_dict[publisher_name]

            # if the subscriber hasn't been already processed yet, determine
            # what is the process_column by selecting the next free column
            # (current_column+1)
            if not subscriber_name in column_dict:
                current_column += 1
                process_column = current_column
                column_dict[subscriber_name] = current_column
                worksheet.write(subscriber_row, current_column,
                                subscriber_name, self.__formats['bold_w_border'])
            else:
                # if the subscriber has been already processed, just set the
                # process_column to the corresponding column
                process_column = column_dict[subscriber_name]

            worksheet.write(process_row, process_column,
                    str(value.get_passed_tests()) + ' / ' +
                        str(value.get_supported_tests()) + ' / ' +
                        str(value.get_total_tests()),
                    self.get_format_color(value.get_passed_tests(), value.get_supported_tests()))

    def add_static_data_summary_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            name: str = 'Summary',
            starting_row: int = 0, # row 1
            starting_column: int = 1): # B column
        """
        Add header to the summary worksheet, it includes the DDS logo, the
        title and subtitle, the repo link and the time when the XLSX report
        was generated. This static data requires 8 rows
        """

        current_row = starting_row

        # Add title
        worksheet.write(
            current_row, starting_column,
            'DDS Interoperability tests', self.__formats['title'])

        # Add Summary literal
        current_row += 1
        worksheet.write(
            current_row, starting_column,
            'Summary', self.__formats['subtitle'])

       # Add DDS logo pic
        current_row += 2
        script_folder = os.path.dirname(__file__)
        dds_logo_path = os.path.join(script_folder, 'resource/DDS-logo.jpg')
        worksheet.insert_image(
            row=current_row, col=starting_column,
            filename=dds_logo_path,
            options={'x_scale': 0.4, 'y_scale': 0.4, 'decorative': True, 'object_position': 2})

        # Add date
        current_row += 1
        worksheet.write(current_row, starting_column + 1, 'Date')
        date_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        worksheet.write(current_row, starting_column + 2, date_time)

        # Add repo link
        current_row += 1
        worksheet.write(current_row, starting_column + 1,'Repo')
        worksheet.write(current_row, starting_column + 2, self.REPO_LINK)

        # Add repo doc link
        current_row += 1
        worksheet.write(current_row, starting_column + 1,'Documentation')
        worksheet.write(current_row, starting_column + 2, self.REPO_DOC)

    def add_static_data_description_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            name: str = 'Test Descriptions',
            starting_row: int = 0, # row 1
            starting_column: int = 1): # B column
        """
        Add header to the test descriptions worksheet, it includes the headers
        of the columns.
        """

        current_row = starting_row

        # Add column headers
        worksheet.write(
            current_row, starting_column,
            'Test Name', self.__formats['product_subtitle'])
        worksheet.write(
            current_row, starting_column + 1,
            'Test Title', self.__formats['product_subtitle'])
        worksheet.write_url(
            current_row, starting_column + 2,
            'https://omg-dds.github.io/dds-rtps/test_description.html',
            string="Click here for full test descriptions")

    def add_test_name_description_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            starting_row: int = 1, # row 2
            col: int = 1): # B column
        """Add test names to the test descriptions worksheet."""

        current_row = starting_row

        # Add test name
        for test_name in test_suite.rtps_test_suite_1.keys():
            worksheet.write(current_row, col, test_name, self.__formats['bold'])
            current_row += 1

    def add_title_description_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            starting_row: int = 1, # row 2
            col: int = 2): # C column
        """Add short test description (aka title) to the test descriptions worksheet."""

        current_row = starting_row

        # Add test title
        for value in test_suite.rtps_test_suite_1.values():
            worksheet.write(current_row, col, value['title'])
            current_row += 1

def get_file_extension(input) -> str:
    """Get file extension from the input as Path or str"""
    input_string = ''
    if isinstance(input, pathlib.Path):
        input_string = str(input)
    elif isinstance(input, str):
        input_string = input
    else:
        raise RuntimeError('get_file_extension error, only Path, or str allowed')
    return os.path.splitext(input_string)[1].lower()[1:]


def main():
    # parse arguments
    argument_parser = XlxsReportArgumentParser.argument_parser()
    args = argument_parser.parse_args()

    options = {
        'input': args.input,
        'output': args.output
    }

    # Get absolute paths from input and output
    if options['input'] is not None:
        input = pathlib.Path(options['input']).resolve()
    else:
        raise RuntimeError('no input file specified')

    # Check if the input and output have the right extension
    if not input.is_file() and get_file_extension(input) != 'xml':
        raise RuntimeError('the input is not a file, or the extension is not xml')

    if options['output'] is not None:
        output = pathlib.Path(options['output']).resolve()
    else:
        raise RuntimeError('no output file specified')

    if output.exists() or get_file_extension(output) != 'xlsx':
        raise RuntimeError('output file already exist or is not pointing to an '
                           + 'xlsl file')

    try:
        # generate a JunitData from the file in the input
        junit_data = JunitData(input=input)
        # generate report in the output from the JunitData
        XlsxReport(output=output, data=junit_data)
    except KeyboardInterrupt:
        print('interrupted by user')
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)
    except Exception as e:
        raise e

if __name__ == '__main__':
    main()
