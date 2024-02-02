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

class XlxsReportArgumentParser:
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

class JunitAggregatedData:
    data: tuple[int,int] # [tests_passed, total_tests]

    def __init__(self, passed_tests: int, total_tests: int) -> None:
        self.data = [passed_tests, total_tests]

    def get_passed_tests(self):
        return self.data[0]

    def get_total_tests(self):
        return self.data[1]

    def __str__(self) -> str:
        return f'({self.data[0]}, {self.data[1]})'

class JunitTesCaseAggregatedData:
    # [publisher or subscriber name, test_name, test_passed]]
    data: tuple[str,str,bool] = None

    def __init__(self, product: str, test_name: str, passed: bool) -> None:
        self.data = (product, test_name, passed)

    def get_product_name(self):
        return self.data[0]

    def get_test_name(self):
        return self.data[1]

    def get_passed(self):
        return self.data[2]

    def __str__(self) -> str:
        return f'{self.data}'

class JunitData:
    summary_dict: dict[str,JunitAggregatedData] = {}
    product_summary_dict: dict[(str,str),JunitAggregatedData] = {}

    publisher_product_dict: dict[str,list[JunitTesCaseAggregatedData]] = {}
    subscriber_product_dict: dict[str,list[JunitTesCaseAggregatedData]] = {}

    @staticmethod
    def xml_parser(file):
        parser = lxml.etree.XMLParser(huge_tree=True)
        return lxml.etree.parse(file, parser)

    def __init__(self, input: pathlib.Path):
        self.get_info(input)

    def update_value_to_summary_dict(self, key: str, value: JunitAggregatedData) -> None:
        if key in self.summary_dict:
            updated_data = JunitAggregatedData(
                self.summary_dict[key].get_passed_tests() + value.get_passed_tests(),
                self.summary_dict[key].get_total_tests() + value.get_total_tests(),
            )
            self.summary_dict[key] = updated_data
        else:
            self.summary_dict[key] = value

    def update_value_to_product_summary_dict(self, key: tuple[str,str], value: JunitAggregatedData) -> None:
        if key in self.product_summary_dict:
            updated_data = JunitAggregatedData(
                self.product_summary_dict[key].get_passed_tests() + value.get_passed_tests(),
                self.product_summary_dict[key].get_total_tests() + value.get_total_tests(),
            )
            self.product_summary_dict[key] = updated_data
        else:
            self.product_summary_dict[key] = value

    def update_value_to_product_dict(self,
            key: str,
            product_dict: dict[str,list[JunitTesCaseAggregatedData]],
            value: JunitTesCaseAggregatedData) -> None:
        if key in product_dict:
            product_dict[key].append(value)
            # self.product_dict[key] = updated_data
        else:
            product_dict[key] = [value]

    def get_info(self, input: pathlib.Path = None):
        xml = junitparser.JUnitXml.fromfile(input, parse_func=self.xml_parser)

        for suite in list(iter(xml)):
            product_names = re.search(r'([\S]+)\-\-\-([\S]+)', suite.name)

            element = JunitAggregatedData(
                    suite.tests - suite.failures - suite.skipped - suite.errors,
                    suite.tests
            )
            publisher_name = product_names.group(1).replace('-', ' ').replace('_', ' ')
            subscriber_name = product_names.group(2).replace('-', ' ').replace('_', ' ')
            self.update_value_to_summary_dict(publisher_name, element)
            self.update_value_to_summary_dict(subscriber_name, element)

            # Get table with the summary of the test passed/total_tests for
            # every product.
            product_dict_key = (publisher_name, subscriber_name)
            product_test_data = JunitAggregatedData(
                passed_tests=suite.tests - suite.failures - suite.skipped - suite.errors,
                total_tests=suite.tests
            )
            self.update_value_to_product_summary_dict(product_dict_key, product_test_data)


            for case in list(iter(suite)):
                test_name = re.search(r'((?:Test_)[\S]+_\d+)', case.name).group(1)

                publisher_test_result = JunitTesCaseAggregatedData(
                    product=subscriber_name,
                    test_name=test_name,
                    passed=case.is_passed
                )

                self.update_value_to_product_dict(
                        key=publisher_name,
                        value=publisher_test_result,
                        product_dict=self.publisher_product_dict
                )

                subscriber_test_result = JunitTesCaseAggregatedData(
                    product=publisher_name,
                    test_name=test_name,
                    passed=case.is_passed
                )

                self.update_value_to_product_dict(
                        key=subscriber_name,
                        value=subscriber_test_result,
                        product_dict=self.subscriber_product_dict
                )

class ColorUtils:
    GREEN = '#4EB168'
    LIME = '#86A336'
    YELLOW ='#B58F19'
    ORANGE = '#DB722e'
    RED = '#F2505A'

class XlsxReport:
    workbook: xlsxwriter.Workbook
    __data: JunitData
    formats: dict = {} # contains the format name and formats objects

    def __init__(self, output: pathlib.Path, data: JunitData):
        self.workbook = xlsxwriter.Workbook(output)
        # set the default workbook size
        self.workbook.set_size(2000,1500)
        self.__data = data
        self.add_formats()
        self.create_summary_worksheet()
        self.add_data_test_worksheet()
        self.workbook.close()

    def set_worksheet_defaults(self, worksheet: xlsxwriter.Workbook.worksheet_class):
        # set default values
        # column width 10 (we won't use more than the 'Z' column)
        worksheet.set_column('A:Z', 12.5)
        worksheet.set_zoom(130)

    def create_summary_worksheet(self,
            name: str = 'Summary'):
        summary_worksheet = self.workbook.add_worksheet(name=name)
        self.set_worksheet_defaults(summary_worksheet)
        self.add_static_data_summary_worksheet(summary_worksheet)
        self.add_data_summary_worksheet(summary_worksheet)

    def add_formats(self):
        self.formats['title'] = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 36,
            'text_wrap': True
        })
        self.formats['product_title'] = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 16,
            'text_wrap': False
        })
        self.formats['subtitle'] = self.workbook.add_format({
            'align': 'center',
            'font_size': 26
        })
        self.formats['product_subtitle'] = self.workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
        })
        self.formats['bold_w_border'] = self.workbook.add_format(properties={'bold': True, 'border': 1})
        self.formats['result_green'] = value_format = self.workbook.add_format(
            properties={'bold': True, 'border': 1, 'bg_color': ColorUtils.GREEN, 'align': 'center', 'valign': 'vcenter',})
        self.formats['result_lime'] = value_format = self.workbook.add_format(
            properties={'bold': True, 'border': 1, 'bg_color': ColorUtils.LIME, 'align': 'center', 'valign': 'vcenter',})
        self.formats['result_yellow'] = value_format = self.workbook.add_format(
            properties={'bold': True, 'border': 1, 'bg_color': ColorUtils.YELLOW, 'align': 'center', 'valign': 'vcenter',})
        self.formats['result_orange'] = value_format = self.workbook.add_format(
            properties={'bold': True, 'border': 1, 'bg_color': ColorUtils.ORANGE, 'align': 'center', 'valign': 'vcenter',})
        self.formats['result_red'] = value_format = self.workbook.add_format(
            properties={'bold': True, 'border': 1, 'bg_color': ColorUtils.RED, 'align': 'center', 'valign': 'vcenter',})

    def get_format_color(self, index: int, num_elements: int):
        ratio = index / num_elements
        if ratio < 0.25:
            return self.formats['result_red']
        elif ratio < 0.5:
            return self.formats['result_orange']
        elif ratio < 0.75:
            return self.formats['result_yellow']
        elif ratio < 1:
            return self.formats['result_lime']
        else: # ratio == 1
            return self.formats['result_green']

    def get_format_color_bool(self, passed: bool):
        if passed:
            return self.get_format_color(1,1)
        else:
            return self.get_format_color(0,1)

    def add_static_data_test(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            product_name: str,
            product_count: int):
        # the last column of the publisher table is
        # `2 (column C) + product_count - 1`
        # the -1 is because the column C is already counted
        last_column_publisher = 1 + product_count
        worksheet.merge_range(
            # row 1, from column C till last_column_publisher
            0, 2, 0, last_column_publisher,
            "Publisher: " + product_name,
            self.formats['product_title'])
        worksheet.merge_range(
            # row 2, from column C till last_column_publisher
            1, 2, 1, last_column_publisher,
            "Subscriber: ",
            self.formats['product_subtitle'])

        # the subscriber table starts at last_column_publisher + 1
        last_column_subscriber = last_column_publisher + 1 + product_count
        worksheet.merge_range(
            # row 1, from column last_column_publisher + 1 till last_column_subscriber
            0, last_column_publisher + 1, 0, last_column_subscriber,
            "Subscriber: " + product_name,
            self.formats['product_title'])
        worksheet.merge_range(
            # row 2, from column last_column_publisher + 1 till last_column_subscriber
            1, last_column_publisher + 1, 1, last_column_subscriber,
            "Publisher: ",
            self.formats['product_subtitle'])
        return (1,last_column_subscriber)

    def add_data_test_worksheet(self):
        # create a list that contains the worksheet names per product. These
        # product names are the same for the publisher and the subscriber
        product_names = []
        for name in self.__data.publisher_product_dict.keys():
            product_names.append(name)

        for name in product_names:
            # truncate the name of the string to 31 chars
            worksheet = self.workbook.add_worksheet((name)[:31])
            self.set_worksheet_defaults(worksheet)

            current_cell = self.add_static_data_test(
                    worksheet=worksheet,
                    product_name=name,
                    product_count=len(product_names))

            # next row
            starting_row = current_cell[0] + 1

            # Add table with the product as publisher
            worksheet.set_column(1, 1, 22)
            current_cell = self.add_product_table(
                worksheet=worksheet,
                product_name=name,
                is_publisher= True,
                starting_column=1, # B
                starting_row=starting_row,
                value=self.__data.publisher_product_dict[name],
                print_test_name=True
            )

            worksheet.set_column(current_cell[1] + 1, current_cell[1] + 1, 4)

            # Add table with the product as subscriber

            # as the test_name is not printed, the starting_column does not
            # write anything, so, the table starts at starting_column + 1
            self.add_product_table(
                worksheet=worksheet,
                product_name=name,
                is_publisher=True,
                starting_column=current_cell[1] + 1, # next column
                starting_row=starting_row,
                value=self.__data.subscriber_product_dict[name],
                print_test_name=False
            )

    def add_product_table(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            product_name: str,
            is_publisher: bool,
            starting_row: int,
            starting_column: int,
            value: list[JunitTesCaseAggregatedData],
            print_test_name: bool):

        current_column = starting_column
        current_row = starting_row
        subscriber_row = starting_row
        test_column = starting_column
        # This column dictionary will keep the colum for the subscriber product
        column_dict = {}
        row_dict = {}
        for element in value:
            if element.get_product_name() in column_dict:
                process_column = column_dict[element.get_product_name()]
            else:
                current_column += 1
                process_column = current_column
                column_dict[element.get_product_name()] = current_column
                worksheet.write(
                        subscriber_row,
                        current_column,
                        element.get_product_name(),
                        self.formats['bold_w_border'])

            if element.get_test_name() in row_dict:
                process_row = row_dict[element.get_test_name()]
            else:
                current_row += 1
                process_row = current_row
                row_dict[element.get_test_name()] = current_row
                if print_test_name:
                    worksheet.write(
                            current_row,
                            test_column,
                            element.get_test_name(),
                            self.formats['bold_w_border'])

            str_result = 'OK' if element.get_passed() else 'ERROR'
            worksheet.write(
                    process_row,
                    process_column,
                    str_result,
                    self.get_format_color_bool(element.get_passed()))
        return (current_row, current_column)

    def add_data_summary_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class):

        worksheet.write('B17', 'Product', self.formats['bold_w_border'])
        worksheet.write('C17', 'Test Passed', self.formats['bold_w_border'])

        # Add AggregatedData
        # column and rows start counting at 0, the spreadsheet column/row number
        # is 1 number higher
        current_column = 1 # column B
        current_row = 17 # row 18
        for key, value in self.__data.summary_dict.items():
            worksheet.write(current_row, current_column, key, self.formats['bold_w_border'])
            worksheet.write(current_row, current_column + 1,
                    str(value.get_passed_tests()) + ' / ' + str(value.get_total_tests()),
                    self.get_format_color(value.get_passed_tests(), value.get_total_tests()))
            current_row += 1

        # Add 2 rows of gap for the next table
        current_row += 2
        worksheet.write(current_row, current_column, "Publisher/Subscriber", self.formats['bold_w_border'])

        # create a dictionary to store the row/column of the product name
        # for example, row_dict['Connext 6.1.2'] = 30 means that the
        # row (publisher) of Connext 6.1.2 is in the row 29.
        # Column for the publisher is always fixed: 1 --> B
        # Row for the subscriber is always fixed: current_row
        subscriber_row = current_row
        publisher_column = 1
        row_dict={} # publishers
        column_dict={} # subscribers

        for key, value in self.__data.product_summary_dict.items():
            # key[0] --> publishers
            if not key[0] in row_dict:
                current_row += 1
                process_row = current_row
                row_dict[key[0]] = current_row
                worksheet.write(current_row, publisher_column, key[0], self.formats['bold_w_border'])
            else:
                process_row = row_dict[key[0]]

            # key[1] --> subscriber
            if not key[1] in column_dict:
                current_column += 1
                process_column = current_column
                column_dict[key[1]] = current_column
                worksheet.write(subscriber_row, current_column, key[1], self.formats['bold_w_border'])
            else:
                process_column = column_dict[key[1]]

            worksheet.write(process_row, process_column,
                    str(value.get_passed_tests()) + ' / ' +str(value.get_total_tests()),
                    self.get_format_color(value.get_passed_tests(), value.get_total_tests()))

    def add_static_data_summary_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class,
            name: str = 'Summary',):

        # Add DDS Logo pic
        script_folder = os.path.dirname(__file__)
        dds_logo_path = os.path.join(script_folder, 'resource/DDS-logo.jpg')
        worksheet.insert_image('B2', dds_logo_path,
                options={'x_scale': 0.6, 'y_scale': 0.6, 'decorative': True})

        # Add title

        # increase size of B column
        worksheet.set_column('B:B', 20.5)
        worksheet.merge_range("C2:F11", "DDS Interoperability tests", self.formats['title'])

        # Add Summary literal
        worksheet.merge_range("B12:G12", "Summary", self.formats['subtitle'])

        # Add repo link
        worksheet.write('B13','Repo')
        worksheet.merge_range("C13:G13", "https://github.com/omg-dds/dds-rtps")

        # Add date
        worksheet.write('B14','Date')
        date_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        worksheet.merge_range("C14:G14", date_time)


def get_file_extension(input) -> str:
    input_string = ''
    if isinstance(input, pathlib.Path):
        input_string = str(input)
    elif isinstance(input, str):
        input_string = input
    else:
        raise Exception('get_file_extension error, only Path, or str allowed')
    return os.path.splitext(input_string)[1].lower()[1:]


def main():
    argument_parser = XlxsReportArgumentParser.argument_parser()
    args = argument_parser.parse_args()

    options = {
        'input': args.input,
        'output': args.output
    }

    if options['input'] is not None:
        input = pathlib.Path(options['input']).resolve()
    else:
        raise RuntimeError("no input file specified")

    if not input.is_file() and get_file_extension(input) != 'xml':
        raise RuntimeError("the input is not a file, or the extension is not xml")

    if options['output'] is not None:
        output = pathlib.Path(options['output']).resolve()
    else:
        raise RuntimeError("no output file specified")

    if output.exists() or get_file_extension(output) != "xlsx":
        raise RuntimeError("output file already exist or is not pointing to an "
                           + "xlsl file")

    try:
        junit_data = JunitData(input=input)
        XlsxReport(output=output, data=junit_data)
    except KeyboardInterrupt:
        print("interrupted by user")
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)
    except Exception as e:
        raise e

if __name__ == '__main__':
    main()
