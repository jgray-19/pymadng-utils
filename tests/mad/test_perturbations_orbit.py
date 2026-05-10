"""Tests for magnet perturbations and orbit correction."""

from __future__ import annotations

import numpy as np
import pytest
import tfs

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface


@pytest.fixture(scope="function")
def lhc_interface(seq_b1):
    """Return a fresh MAD interface with LHC perturbation metadata enabled."""
    interface = AcceleratorMadInterface(
        accelerator=LHC(beam=1, sequence_file=seq_b1, kinetic_energy=6800.0)
    )
    yield interface
    interface.close()


def _get_element_attr(
    interface: AcceleratorMadInterface, element_name: str, attr: str
) -> float:
    return float(interface.mad.loaded_sequence[element_name][attr])


def _get_effective_strength(
    interface: AcceleratorMadInterface, element_name: str, attr: str
) -> float:
    return interface.get_magnet_strengths([f"{element_name}.{attr}"])[f"{element_name}.{attr}"]


def _get_perturbation_knob_name(element_name: str, attr: str) -> str:
    knob_attr = f"d{attr}l" if attr in {"k0", "k1", "k2"} else attr
    return f"{element_name}.{knob_attr}"


def test_effective_strength_matches_base_when_dknl_not_created(
    lhc_interface: AcceleratorMadInterface,
) -> None:
    """Effective strength should fall back to the base strength before perturbation."""
    quad_name = "MQY.B5L2.B1"

    assert len(lhc_interface.mad.loaded_sequence[quad_name].dknl) == 0
    assert np.isclose(
        _get_effective_strength(lhc_interface, quad_name, "k1"),
        _get_element_attr(lhc_interface, quad_name, "k1"),
    )


@pytest.mark.parametrize(
    ("rel_error", "expect_non_table_changed"),
    [(None, False), (1e-2, True)],
    ids=["table_relative_errors", "global_relative_error"],
)
def test_lhc_quadrupole_perturbation_modes(
    lhc_interface: AcceleratorMadInterface,
    rel_error: float | None,
    expect_non_table_changed: bool,
) -> None:
    """LHC quadrupole perturbation should support table and global modes."""
    table_family_quad = "MQY.B5L2.B1"
    non_table_quad = "MQT.12R2.B1"

    k1_table_before = _get_effective_strength(lhc_interface, table_family_quad, "k1")
    k1_non_table_before = _get_effective_strength(lhc_interface, non_table_quad, "k1")

    magnet_strengths, _ = lhc_interface.apply_magnet_perturbations(
        rel_error=rel_error,
        seed=42,
        magnet_type="q",
    )

    k1_table_after = _get_effective_strength(lhc_interface, table_family_quad, "k1")
    k1_non_table_after = _get_effective_strength(lhc_interface, non_table_quad, "k1")

    assert not np.isclose(k1_table_after, k1_table_before)
    non_table_rel_change = abs(k1_non_table_after - k1_non_table_before) / max(
        abs(k1_non_table_before), 1e-12
    )
    assert (non_table_rel_change > 1e-3) == expect_non_table_changed
    assert _get_perturbation_knob_name(table_family_quad, "k1") in magnet_strengths
    if expect_non_table_changed:
        assert _get_perturbation_knob_name(non_table_quad, "k1") in magnet_strengths


def test_perform_orbit_correction_writes_corrector_table_and_matches_tunes(
    lhc_interface: AcceleratorMadInterface,
    tmp_path,
) -> None:
    """Orbit correction should export correctors and rematch tunes."""
    corrector_file = tmp_path / "correctors.tfs"
    lhc_interface.mad["zero_twiss", "_"] = lhc_interface.mad.twiss(sequence="loaded_sequence")

    matched_tunes = lhc_interface.perform_orbit_correction(
        machine_deltap=0.0,
        target_qx=0.28,
        target_qy=0.31,
        corrector_file=corrector_file,
    )

    assert corrector_file.exists()
    corrector_table = tfs.read(corrector_file)
    assert not corrector_table.empty
    assert {"ename", "kind"}.issubset(corrector_table.columns)
    assert set(matched_tunes) == {"dqx_b1_op", "dqy_b1_op"}

    lhc_interface.mad.send("""
local tbl = twiss {sequence=loaded_sequence, observe=0, deltap=0.0}
py:send({tbl.q1, tbl.q2}, true)
""")
    q1, q2 = lhc_interface.mad.recv()
    assert q1 == pytest.approx(62.28, abs=1e-5)
    assert q2 == pytest.approx(60.31, abs=1e-5)
