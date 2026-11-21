from __future__ import annotations

import sys
from importlib.metadata import version as package_version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

project = "pymadng-utils"
author = "pymadng-utils contributors"
release = package_version("pymadng-utils")

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autosummary_generate = True
autosummary_imported_members = False
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autoclass_content = "both"
napoleon_google_docstring = True
napoleon_numpy_docstring = True

autodoc_mock_imports = [
    "cpymad",
    "numpy",
    "omc3",
    "pandas",
    "pymadng",
    "tfs",
]

html_theme = "furo"
html_static_path = ["_static"]
html_title = "pymadng-utils"
html_theme_options = {
    "source_repository": "https://github.com/jgray-19/pymadng-utils/",
    "source_branch": "main",
    "source_directory": "docs/",
}
