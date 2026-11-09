import pathlib
import tomllib
from datetime import UTC, datetime

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "specvizitor"
author = "Ivan Kramarenko, Josephine Kerutt"
copyright = f"2023–{datetime.now(tz=UTC).year}, " + author

# defined once, in pyproject.toml
with open(pathlib.Path(__file__).parent.parent / 'pyproject.toml', 'rb') as f:
    release = tomllib.load(f)['project']['version']

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

extlinks = {
    'pypi': ('https://pypi.org/project/%s', '%s')
}
extensions += [
    'sphinx.ext.extlinks',
    'sphinx_copybutton',
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_book_theme'
html_theme_options = {
    "repository_url": "https://github.com/ivkram/specvizitor",
    "use_repository_button": True,
    "use_issues_button": True
}
