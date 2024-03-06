from datetime import date

from textmate_grammar import __version__

# -- Project information -----------------------------------------------------

project = "textmate-grammar-python"
version = __version__
copyright = f"{date.today().year}, Mark Shui Hu"
author = "Mark Shui Hu"

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "autodoc2",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
}
myst_enable_extensions = ["fieldlist", "deflist"]

# -- HTML output -------------------------------------------------

html_theme = "furo"
html_title = "textmate-grammar-python"
html_theme_options = {
    "top_of_page_button": "edit",
    "source_repository": "https://github.com/watermarkhu/textmate-grammar-python/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# --- Autodoc configuration ------

autodoc2_packages = ["../src/textmate_grammar"]
autodoc2_hidden_objects = ["dunder", "private", "inherited"]

