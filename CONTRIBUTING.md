# Contributing

1. Clone the repository and install with the dev and test extras: `uv sync --extra dev --extra test`.
2. Install the hooks once: `uv run pre-commit install` (ruff, whitespace, commit-message check).
3. Run the tests: `uv run pytest`. Most tests start MAD-NG or MAD-X and use the fixtures in `tests/data`; the full suite takes a few minutes.
4. Format and lint with a line length of 100: `uv run ruff format src tests` and `uv run ruff check src tests`.
5. Build the docs with `uv sync --extra docs` then `uv run sphinx-build -W -b html docs docs/_build/html`.

Changes to public behaviour need a test of the physical result and a line in `CHANGELOG.md`. The API is not kept backwards compatible while the package is alpha.
