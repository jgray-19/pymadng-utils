"""TFS file format conversion utilities."""

import logging
from pathlib import Path

import pandas as pd
import tfs

LOGGER = logging.getLogger(__name__)


def convert_tfs_to_madx(tfs_df: pd.DataFrame, remove_drifts=True) -> pd.DataFrame:
    """
    Convert TFS DataFrame from MAD-NG format to MAD-X format.

    This function performs the following transformations:

    - Drops every column whose name is not lowercase (MAD-NG's extra columns)
    - Converts the remaining column names and all header keys to uppercase
    - Renames phase advance columns: 'MU1' → 'MUX', 'MU2' → 'MUY' (keeps existing MUX/MUY)
    - If ``remove_drifts``, renames the elements of kind ``drift`` whose name starts with
      "drift" to consecutive DRIFT_0, DRIFT_1, ...
    - Sets 'NAME' as index and removes special rows ('$start', '$end')

    Args:
        tfs_df: Input TFS DataFrame in MAD-NG format.
        remove_drifts: Renumber the drift elements as described above.

    Returns:
        Converted TFS DataFrame in MAD-X format.
    """
    # Reset the index to manipulate columns
    tfs_df = tfs_df.reset_index()

    # Make the headers all upper case for consistency
    tfs_df.headers = {k.upper(): v for k, v in tfs_df.headers.items()}

    # Remove all columns that are not lowercase.
    drop_columns = [col for col in tfs_df.columns if not col.islower()]
    tfs_df = tfs_df.drop(columns=drop_columns)

    # Make the columns all upper case for consistency
    tfs_df.columns = [col.upper() for col in tfs_df.columns]

    # Change MU1 and MU2 to MUX and MUY column names. If MUX/MUY already exist
    # (e.g. a hybrid xsuite twiss carrying both 'mux'/'muy' and 'mu1'/'mu2'),
    # keep them and drop MU1/MU2 to avoid duplicate columns; otherwise rename.
    if "MUX" in tfs_df.columns:
        tfs_df = tfs_df.drop(columns=["MU1", "MU2"], errors="ignore")
    else:
        tfs_df = tfs_df.rename(columns={"MU1": "MUX", "MU2": "MUY"})

    # Renumber drift elements consecutively
    if remove_drifts:
        drifts = tfs_df[
            (tfs_df["KIND"] == "drift") & (tfs_df["NAME"].str.lower().str.startswith("drift"))
        ]
        if not drifts.empty:
            new_drift_names = [f"DRIFT_{i}" for i in range(len(drifts))]
            tfs_df.loc[drifts.index, "NAME"] = new_drift_names

    # Set NAME as index and filter out special markers
    tfs_df = tfs_df.set_index("NAME")
    return tfs_df.filter(regex=r"^(?!\$start|\$end).*$", axis="index")


def export_tfs_to_madx(tfs_file: Path) -> None:
    """
    Read a TFS file, convert to MAD-X format, and overwrite the original.

    This is a convenience function that reads a TFS file, applies the
    MAD-NG to MAD-X conversion, and writes it back.

    Args:
        tfs_file: Path to the TFS file to convert.

    Raises:
        FileNotFoundError: If the TFS file doesn't exist.
    """
    if not tfs_file.exists():
        raise FileNotFoundError(f"TFS file not found: {tfs_file}")

    tfs_df = tfs.read(tfs_file)
    tfs_df = convert_tfs_to_madx(tfs_df)
    tfs.write(tfs_file, tfs_df, save_index="NAME")

    LOGGER.info(f"Converted TFS file to MAD-X format: {tfs_file.name}")


def convert_multiple_tfs_files(tfs_files: list[Path]) -> None:
    """
    Convert multiple TFS files to MAD-X format.

    Args:
        tfs_files: List of TFS file paths to convert.
    """
    for tfs_file in tfs_files:
        export_tfs_to_madx(tfs_file)
