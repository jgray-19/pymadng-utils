"""
Tests for pymadng_utils.io.utils module.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

from pymadng_utils.io.utils import read_knobs, save_knobs


@pytest.fixture
def temp_file() -> Generator[Path, None, None]:
    """Fixture to create and clean up temporary files."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


class TestReadKnobs:
    """Tests for read_knobs function."""

    @pytest.mark.parametrize(
        "content,expected",
        [
            (
                "knob1\t1.23e-05\nknob2\t-2.35e-04\n",
                {
                    "knob1": 1.23e-05,
                    "knob2": -2.35e-04,
                },
            ),
            ("", {}),
            ("knob1\t1.0\ninvalid_line\nknob2\t2.0\n", {"knob1": 1.0, "knob2": 2.0}),
        ],
    )
    def test_read_knobs(
        self, temp_file: Path, content: str, expected: dict[str, float]
    ) -> None:
        """Test reading knobs from files."""
        temp_file.write_text(content)
        result = read_knobs(str(temp_file))
        assert result == expected


class TestSaveKnobs:
    """Tests for save_knobs function."""

    @pytest.mark.parametrize(
        "knobs,expected_content",
        [
            (
                {"knob1": 1.23e-05, "knob2": -2.35e-04},
                "knob1\t 1.230000000000000e-05\nknob2\t-2.350000000000000e-04\n",
            ),
            ({}, ""),
        ],
    )
    def test_save_knobs(
        self, temp_file: Path, knobs: dict[str, float], expected_content: str
    ) -> None:
        """Test saving knobs to file."""
        save_knobs(knobs, temp_file)
        content = temp_file.read_text()
        assert content == expected_content
