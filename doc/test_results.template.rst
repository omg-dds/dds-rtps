.. include:: vars.rst

.. _section-test-results:


Test Results
============

The test results are presented in a spreadsheet containing multiple tabs.

The first tab presents a summary of the tests per product:

* The first table shows the number of passed tests versus total tests, offering
  a quick overview of vendor compliance. The result is reported using the notation
  (NumberPassedTests / NumberTotalTests). Colors are also used to highlight the
  level of interoperability (green being the best and red the worst)
* The second table shows more detail on the interoperability between each pair
  of products: One product acting as **Publishers** (rows) and one as **Subscriber**
  (columns). The result is again reported using the notation
  (NumberPassedTests / NumberTotalTests).

The second tab contains a summary of the test descriptions. The full details can
be found in the `Test Descriptions section <https://omg-dds.github.io/dds-rtps/test_description.html>`__.

The remaining tabs in the spreadsheet (see tab selection at the bottom of the
spreadsheet) contain the individual test case results per product. Each tab
is named after the respective product and contains two tables:

* Left-side table: Current product as publisher and all products as subscribers.
* Right-side table: Current product as subscriber and all products as publishers.

Access the report at: |LINK_XLSX_URL|

.. raw:: html

    <iframe src="|LINK_XLSX_URL|" width="100%" height="800"></iframe>
