from pathlib import Path

import pandas as pd
import pytest

from pymadng_utils.madx.tfs_utils import (
    convert_tfs_to_madx,
    export_tfs_to_madx,
)


def _sample_tfs_dataframe():
    tfs = pytest.importorskip("tfs")
    df = tfs.TfsDataFrame(
        {
            "kind": ["marker", "drift", "quadrupole", "drift", "marker"],
            "mu1": [0.0, 0.1, 0.2, 0.3, 0.4],
            "mu2": [0.0, 0.1, 0.2, 0.3, 0.4],
            "disp1": [0.0, 0.0, 0.0, 0.0, 0.0],
            "disp2": [0.0, 0.0, 0.0, 0.0, 0.0],
            "disp3": [0.0, 0.0, 0.0, 0.0, 0.0],
            "disp4": [0.0, 0.0, 0.0, 0.0, 0.0],
        },
        index=pd.Index(["$start", "drift_a", "mq.1", "drift_b", "$end"], name="name"),
    )
    df.headers = {"q1": 62.28, "q2": 60.31}
    return df


def test_convert_tfs_to_madx_renames_columns_and_filters_markers() -> None:
    converted = convert_tfs_to_madx(_sample_tfs_dataframe())

    assert "MUX" in converted.columns
    assert "MUY" in converted.columns
    assert "DX" in converted.columns
    assert "DPX" in converted.columns
    assert "DY" in converted.columns
    assert "DPY" in converted.columns
    assert "$start" not in converted.index
    assert "$end" not in converted.index
    assert "DRIFT_0" in converted.index
    assert "DRIFT_1" in converted.index


def test_export_tfs_to_madx_raises_for_missing_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.tfs"
    with pytest.raises(FileNotFoundError):
        export_tfs_to_madx(missing_file)
