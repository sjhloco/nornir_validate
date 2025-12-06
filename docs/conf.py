import sys
from importlib.metadata import version as get_version
from pathlib import Path

# Add your package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Nornir Validate"
copyright = "2025, sjhloco"  # noqa: A001
author = "sjhloco"

# Get version from package
version = release = get_version("nornir-validate")


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

html_theme_options = {
    "navigation_depth": 3,  # Make sure it's not 0
    "collapse_navigation": False,
    "titles_only": False,
}
