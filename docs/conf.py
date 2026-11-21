from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

project = "pymadng-utils"
author = "pymadng-utils contributors"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

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

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_title = "pymadng-utils"
