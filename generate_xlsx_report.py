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
    # [subscriber_product_name, test_name, test_passed]]
    data: tuple[str,str,bool] = None

    def __init__(self, subscriber_product: str, test_name: str, passed: bool) -> None:
        self.data = (subscriber_product, test_name, passed)

    def get_passed(self, subscriber_product: str):
        return self.data[subscriber_product][0]

    def get_subscriber_name(self):
        return self.data[0]

    def get_test_name(self):
        return self.data[1]

    def get_passed(self):
        return self.data[2]

    def __str__(self) -> str:
        return f'{self.data}'

# class JunitProductAggregatedData:
#     # [subscriber_product, [tests_passed, total_tests]]
#     data: dict[str, tuple[int,int]]

#     def __init__(self, subscriber_product: str, passed_tests: int, total_tests: int) -> None:
#         self.data = [subscriber_product, passed_tests, total_tests]

#     def get_passed_tests(self, subscriber_product: str):
#         return self.data[subscriber_product][0]

#     def get_total_tests(self, subscriber_product: str):
#         return self.data[subscriber_product][1]

#     def __str__(self) -> str:
#         str_representation = ''
#         for e in self.data.keys():
#             str_representation += f'"{e}": ({self.data[0]}, {self.data[1]})\n'

# class JunitTesCaseAggregatedData:
#     data: tuple[int,int] # [tests_passed, total_tests]

#     def __init__(self, passed_tests: int, total_tests: int) -> None:
#         self.data = [passed_tests, total_tests]

#     def get_passed_tests(self):
#         return self.data[0]

#     def get_total_tests(self):
#         return self.data[1]

#     def __str__(self) -> str:
#         return f'({self.data[0]}, {self.data[1]})'

class JunitTestCaseData:
    # [product_name_publisher, product_name_subscriber, passed]
    data: tuple[str,str,bool] = None
    # list of tuples that contains the XML attributes, [name, value]
    attributes: list(tuple[str,str]) = None
    current_attribute: int = 0

    def __init__(self, publisher: str, subscriber: str, passed: bool, case: junitparser.TestCase) -> None:
        self.data = [publisher, subscriber, passed]
        self.add_custom_attributes(case)

    def get_publisher_name(self):
        return self.data[0]

    def get_subscriber_name(self):
        return self.data[1]

    def get_passed(self):
        return self.data[2]

    def get_attributes(self):
        return self.attributes

    def get_next_attribute(self):
        current = (self.attributes[self.current_attribute]
                if self.current_attribute < len(self.attributes)
                else None)
        self.current_attribute += 1
        return current

    def add_custom_attributes(self, case: junitparser.TestCase) -> list(tuple[str,str]):
        self.attributes = re.findall(r'((?:(?:Publisher)|(?:Subscriber))_\d+)="([\w\-\s]+)"',
                    str(case))

        # check that our tuples contain always 2 elements
        for a in self.attributes:
            if (len(a) % 2 != 0):
                raise Exception("Error retrieving custom attributes")

    def __str__(self) -> str:
        return f'{self.data}; {self.attributes}'


# class JunitTestCaseFeatureData:
#     # [product_name, passed_tests, total_tests]
#     data: tuple[str,int,int] = None

#     def __init__(self, product_name: str, passed: bool) -> None:
#         self.data = [product_name, passed]

#     def get_product_name(self):
#         return self.data[0]

#     def get_passed_tests(self):
#         return self.data[1]

#     def get_total_tests(self):
#         return self.data[2]

#     def __str__(self) -> str:
#         return f'{self.data}'


class JunitData:
    summary_dict: dict[str,JunitAggregatedData] = {}
    test_dict: dict[str,list[JunitTestCaseData]] = {}
    #feature_dict: dict[str,list[JunitTestCaseFeatureData]] = {}
    product_test_dict: dict[str,list[JunitTesCaseAggregatedData]] = {}
    product_summary_dict: dict[(str,str),JunitAggregatedData] = {}

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

    # def update_value_to_testcase_dict(self, key: str, value: JunitTestCaseData) -> None:
    #     if key in self.test_dict:
    #         updated_data = self.test_dict[key].append(value)
    #         self.summary_dict[key] = updated_data
    #     else:
    #         self.test_dict[key] = [value]

    def update_value_to_product_summary_dict(self, key: tuple[str,str], value: JunitAggregatedData) -> None:
        if key in self.product_summary_dict:
            updated_data = JunitAggregatedData(
                self.product_summary_dict[key].get_passed_tests() + value.get_passed_tests(),
                self.product_summary_dict[key].get_total_tests() + value.get_total_tests(),
            )
            self.product_summary_dict[key] = updated_data
        else:
            self.product_summary_dict[key] = value

    def update_value_to_product_test_dict(self, key: str, value: JunitTesCaseAggregatedData) -> None:
        if key in self.product_test_dict:
            self.product_test_dict[key].append(value)
            # self.product_test_dict[key] = updated_data
        else:
            self.product_test_dict[key] = [value]

    # def update_value_to_feature_dict(self, key: str, value: JunitTestCaseFeatureData) -> None:
    #     if key in self.feature_dict:
    #         updated_data = JunitTestCaseFeatureData(
    #             self.feature_dict[key].get_passed_tests() + value.get_passed_tests(),
    #             self.feature_dict[key].get_total_tests() + value.get_total_tests(),
    #         )
    #         self.feature_dict[key] = updated_data
    #     else:
    #         self.feature_dict[key] = [value]

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

                # test_result = JunitTestCaseData(
                #     publisher=publisher_name,
                #     subscriber=subscriber_name,
                #     passed=case.is_passed,
                #     case=case)

                # self.update_value_to_testcase_dict(key=test_name, value=test_result)

                product_test_result = JunitTesCaseAggregatedData(
                    subscriber_product=subscriber_name,
                    test_name=test_name,
                    passed=case.is_passed
                )

                self.update_value_to_product_test_dict(key=publisher_name, value=product_test_result)

                # Get the results per feature
                #feature = re.search(f'(?:Test_)([\S]+)_\d', case.name).group(1)


        # for k in self.product_summary_dict.keys():
        #     print(f'{k}: {self.product_summary_dict[k]}')
        # return

        # for k in self.product_test_dict.keys():
        #     print(f'{k}:')
        #     for e in self.product_test_dict[k]:
        #         print(f'\t{e}')
        # return

        # for k in self.test_dict.keys():
        #     print(f'{k}:')
        #     for e in self.test_dict[k]:
        #         print(f'\t{e}')
        # return
        # for k in self.summary_dict.keys():
        #     print(f'{k}: {self.summary_dict[k]}')
        # return
class ColorUtils:
    GREEN = '#4EB168'
    LIME = '#86A336'
    YELLOW ='#B58F19'
    ORANGE = '#DB722e'
    RED = '#F2505A'
    # @staticmethod
    # def interpolate_color(highest_color, lowest_color, ratio):
    #     r1, g1, b1 = int(highest_color[1:3], 16), int(highest_color[3:5], 16), int(highest_color[5:7], 16)
    #     r2, g2, b2 = int(lowest_color[1:3], 16), int(lowest_color[3:5], 16), int(lowest_color[5:7], 16)
    #     if r1 < r2:
    #         r = int(r1 + (1 - ratio) * (r2 - r1))
    #         print(f'{r} = int({r1} + (1 - {ratio}) * ({r2} - {r1})')
    #     else:
    #         r = int(r2 + ratio * (r1 - r2))
    #         print(f'{r} = int({r2} + {ratio} * ({r1} - {r2})')
    #     if g1 < g2:
    #         g = int(g1 + (1 - ratio) * (g2 - g1))
    #         print(f'{r} = int({g1} + (1 - {ratio}) * ({g2} - {g1})')
    #     else:
    #         g = int(g2 + ratio * (g1 - g2))
    #         print(f'{g} = int({g2} + {ratio} * ({g1} - {g2})')
    #     if b1 < b2:
    #         b = int(b1 + (1 - ratio) * (b2 - b1))
    #         print(f'{b} = int({b1} + (1 - {ratio}) * ({b2} - {b1})')
    #     else:
    #         b = int(b2 + ratio * (b1 - b2))
    #         print(f'{b} = int({b2} + {ratio} * ({b1} - {b2})')
    #     return "#{:02X}{:02X}{:02X}".format(r, g, b)

    # @staticmethod
    # def interpolate_color_at_index(color_higher, color_lower, num_elements, index):
    #     ratio = index / (num_elements)
    #     if ratio < 0.25:
    #         return ColorUtils.RED
    #     elif ratio < 0.5:
    #         return ColorUtils.ORANGE
    #     elif ratio < 0.75:
    #         return ColorUtils.YELLOW
    #     elif ratio < 1:
    #         return ColorUtils.LIME
    #     else: # ratio == 1
    #         return ColorUtils.GREEN
    #     return ColorUtils.interpolate_color(color_higher, color_lower, ratio)

    # @staticmethod
    # def interpolate_green_red_at_index(num_elements, index):
    #     return ColorUtils.interpolate_color_at_index(
    #         ColorUtils.GREEN, ColorUtils.RED, num_elements, index)

class XlsxReport:
    workbook: xlsxwriter.Workbook
    __data: JunitData
    formats: dict = {} # contains the format name and formats objects

    def __init__(self, output: pathlib.Path, data: JunitData):
        self.workbook = xlsxwriter.Workbook(output)
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
        self.formats['subtitle'] = self.workbook.add_format({
            'align': 'center',
            'font_size': 26
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

    def add_data_test_worksheet(self):
        for publisher_name, value in self.__data.product_test_dict.items():
            # truncate the name of the string to 31 chars
            worksheet = self.workbook.add_worksheet(('Pub ' + publisher_name)[:31])
            self.set_worksheet_defaults(worksheet)
            worksheet.set_column('B:B', 35)


            worksheet.write('B2', 'Publisher ' + publisher_name + ' / Subscriber' , self.formats['bold_w_border'])

            current_column = 1 # column B
            current_row = 1 # row 2
            subscriber_row = 1 # row 2
            test_column = 1 # column B
            # This column dictionary will keep the colum for the subscriber product
            column_dict = {}
            row_dict = {}
            for element in value:
                if element.get_subscriber_name() in column_dict:
                    process_column = column_dict[element.get_subscriber_name()]
                else:
                    current_column += 1
                    process_column = current_column
                    column_dict[element.get_subscriber_name()] = current_column
                    worksheet.write(
                            subscriber_row,
                            current_column,
                            element.get_subscriber_name(),
                            self.formats['bold_w_border'])

                if element.get_test_name() in row_dict:
                    process_row = row_dict[element.get_test_name()]
                else:
                    current_row += 1
                    process_row = current_row
                    row_dict[element.get_test_name()] = current_row
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


    def add_data_summary_worksheet(self,
            worksheet: xlsxwriter.Workbook.worksheet_class):

        worksheet.write('B18', 'Product', self.formats['bold_w_border'])
        worksheet.write('C18', 'Test Passed', self.formats['bold_w_border'])

        # Add AggregatedData
        # column and rows start counting at 0, the spreadsheet column/row number
        # is 1 number higher
        current_column = 1 # column B
        current_row = 18 # row 19
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
