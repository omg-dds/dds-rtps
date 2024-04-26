# -*- coding: utf-8 -*-
#
# DDS Interoperability Tests documentation build configuration file, created by
# sphinx-quickstart
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import glob
# sys.path.insert(0, os.path.abspath('.'))
import sphinx_rtd_theme

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gdrive_url import xlsx_url, zip_url

def find_index_html():
    # Get the directory of the script
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory of the script directory
    parent_directory = os.path.abspath(os.path.join(script_directory, '..'))

    # Define the pattern to search for
    pattern = os.path.join(parent_directory, 'index_*.html')

    # Use glob to find files matching the pattern
    matching_files = glob.glob(pattern)

    # Return the first matching file, if any
    return matching_files[0] if matching_files else None


# replacement is defined as
# replacements = {
#     '|VARIABLE_NAME|': 'replacement_value',
#     # Add more replacements as needed
# }

def replace_in_rst_files(replacements):
    # Get the directory of the script
    directory = os.path.dirname(os.path.abspath(__file__))

    # Get a list of all _template.rst files in the directory
    template_files = [f for f in os.listdir(directory) if f.endswith('_template.rst')]

    for template_file in template_files:
        # Construct paths for template and output files
        template_file_path = os.path.join(directory, template_file)
        output_file_path = os.path.join(directory, template_file.replace('_template.rst', '.rst'))

        # Read the content of the template file
        with open(template_file_path, 'r') as file:
            content = file.read()

        # Perform replacements in the content
        for target, replacement in replacements.items():
            content = content.replace(target, replacement)

        # Write the modified content to the output file
        with open(output_file_path, 'w') as file:
            file.write(content)

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.imgmath',
              'sphinx.ext.extlinks',
              'sphinx.ext.imgconverter',]

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'DDS Interoperability Tests'
copyright = '2024, Object Management Group, Inc'
author = 'Object Management Group, Inc'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The full version, including alpha/beta/rc tags.
release = '1.1.2024'
version = release

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '*_template.rst']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

numfig = True
numfig_format = {'figure': 'Figure %s',
                 'table': 'Table %s',
                 'code-block': 'Listing %s',
                 'section': 'Section %s'}

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
# Override default css to get a larger width for local build

def setup(app):
    app.add_css_file('css/custom.css')
    #app.add_javascript('js/custom.js')
# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}
html_logo = "_static/img/DDS-logo.jpg"
html_favicon = "_static/img/favicon.ico"
html_css_files = ['css/custom.css']
html_js_files = ['js/custom.js']

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
# This is required for the alabaster theme
# refs: http://alabaster.readthedocs.io/en/latest/installation.html#sidebars
html_sidebars = {
    '**': [
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
    ]
}

# -- links
LINK_XLSX_URL = xlsx_url
LINK_ZIP_URL = zip_url
INDEX_HTML_PATH = find_index_html()
if INDEX_HTML_PATH is None:
    print ('Error getting INDEX_HTML_PATH')
    exit(1)

replacements = {
    '|LINK_XLSX_URL|': LINK_XLSX_URL,
    '|INDEX_HTML_PATH|': INDEX_HTML_PATH,
    # Add more replacements as needed
}
replace_in_rst_files(replacements)

rst_epilog = """
.. |LINK_ZIP_URL| replace:: {zip_url}
""".format(
zip_url = LINK_ZIP_URL,
)

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'DDS_Interoperability_Tests'



