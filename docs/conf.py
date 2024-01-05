# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

from docutils import nodes, utils

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Anemic Framework"
copyright = "2024, Interjektio Oy"
author = "Interjektio Oy"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "sphinx.ext.doctest",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "hoverxref.extension",
]

hoverxref_role_types = {
    "hoverxref": "tooltip",
    "ref": "modal",
    "confval": "tooltip",
    "mod": "modal",
    "class": "modal",
    "obj": "tooltip",
}

hoverxref_domains = [
    "py",
    "cite",
    "python",
    "readthedocs",
    "venusian",
]

hoverxref_intersphinx_types = {
    # make specific links to use a particular tooltip type
    "readthedocs": {
        "doc": "modal",
        "ref": "tooltip",
    },
    "python": {
        "class": "modal",
        "ref": "tooltip",
    },
    "venusian": {
        "class": "modal",
        "ref": "tooltip",
    },
    # make all links for Sphinx to be ``tooltip``
    "sphinx": "tooltip",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
smartquotes = False
master_doc = "index"
htmlhelp_basename = "anemic"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "venusian": ("https://docs.pylonsproject.org/projects/venusian/en/latest/", None),
}


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ["_static"]
html_theme = "sphinx_rtd_theme"
html_theme_options = {}

html_context = {
    "display_github": True,
    "github_user": "tetframework",
    "github_repo": "anemic",
    "github_version": "main",
    "conf_py_path": "/docs/",
}

html_css_files = [
    "custom.css",
]

always_document_param_types = True
typehints_defaults = "comma"


# The following adapted from Pyramid sphinx documentation configuration
def lib_role(role, rawtext, text, lineno, inliner, options=None, content=None):
    options = options or {}
    """Allow using :lib:`Anemic` for references"""
    if "class" in options:
        assert "classes" not in options
        options["classes"] = options["class"]
        del options["class"]

    return [nodes.inline(rawtext, utils.unescape(text), **options)], []


epub_exclude_files = ["search.html"]


def setup(app):
    app.add_role("lib", lib_role)


# -- Define import paths for autodoc -----------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#module-sphinx.ext.autodoc

sys.path.insert(0, os.path.abspath("../src/"))
