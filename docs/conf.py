# sphinx configuration file

import os
import sys

html_theme = "sphinx_rtd_theme"

# -- Project information -----------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]

sys.path.insert(0, os.path.abspath("../src"))
