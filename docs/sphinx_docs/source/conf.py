# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import sphinx_rtd_theme
import sphinx
sys.path.insert(0, os.path.abspath('../../../'))
sys.path.insert(0, os.path.abspath('../../../jockbot/'))

# sys.path.insert(0, os.path.abspath('../../../jockbot_old/'))

# -- Project information -----------------------------------------------------

project = 'JockBot'
copyright = '2023, Alex Friedman/nysugfx'
author = 'Alex Friedman/nysugfx'

# The full version, including alpha/beta/rc tags
release = '0.0.1'


extensions = ['sphinx.ext.duration',
              'sphinx.ext.doctest',
              'sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              'sphinx.ext.autosummary',
              'sphinx.ext.intersphinx',
              'sphinx.ext.inheritance_diagram',
              'sphinx.ext.autosectionlabel',
              'sphinx.ext.napoleon'
              ]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']
autodoc_inherit_docstrings = True

templates_path = ['_templates']

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']

epub_show_urls = 'footnote'
