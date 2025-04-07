# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath("../"))
sys.path.insert(0, os.path.abspath("../components/niagads"))
# sys.path.insert(0, os.path.abspath("../"))


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "NIAGADS-pylib"
copyright = f"{date.today().year}, University of Pennsylvania"
author = "NIAGADS"
release = "0.0.1-alpha.0"


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


extensions = [
    "autoclasstoc",
    "sphinx.ext.autodoc",
    "autoapi.extension",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_annotation",
    "sphinx_autodoc_typehints",
]


# https://sphinx-autoapi.readthedocs.io/en/latest/

autoapi_keep_files = True  # https://sphinx-autoapi.readthedocs.io/en/latest/how_to.html#how-to-transition-to-manual-documentation
autoapi_dirs = [
    "../components",
    # "../bases",
]
autoapi_type = "python"
autoapi_options = [
    "members",
    "undoc-members",
    "show-module-summary",
    "private-members",
    "special-members",
    # "imported-members",
]

autodoc_typehints = "description"
napoleon_google_docstring = True
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
autodoc_member_order = "bysource"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
#
# html_theme = 'alabaster'
html_theme = "sphinx_rtd_theme"
# html_theme = "sphinxawesome_theme"
html_static_path = ["_static"]
