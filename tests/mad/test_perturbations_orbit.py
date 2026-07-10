"""Tests for magnet perturbations and orbit correction."""

from __future__ import annotations

import contextlib

import numpy as np
import pytest
import tfs

from pymadng_utils.accelerators import LHC
from pymadng_utils.mad.accelerator_mad_interface import AcceleratorMadInterface

KE = 6800  # Beam energy in GeV


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


def test_set_magnet_strengths_absolute_roundtrips_through_dknl(
    lhc_interface: AcceleratorMadInterface,
) -> None:
    """Setting an absolute ``.k1`` folds into dknl and reads back via get_magnet_strengths."""
    quad_name = "MQY.B5L2.B1"
    base = _get_element_attr(lhc_interface, quad_name, "k1")
    target = base + 1e-4

    lhc_interface.set_magnet_strengths({f"{quad_name}.k1": target})

    # Base field is untouched; the perturbation lives in the deferred dknl table.
    assert np.isclose(_get_element_attr(lhc_interface, quad_name, "k1"), base)
    assert len(lhc_interface.mad.loaded_sequence[quad_name].dknl) != 0
    assert np.isclose(_get_effective_strength(lhc_interface, quad_name, "k1"), target)


def test_set_magnet_strengths_integrated_delta_knob(
    lhc_interface: AcceleratorMadInterface,
) -> None:
    """An integrated ``.dk1l`` knob is stored verbatim in dknl and read back directly."""
    quad_name = "MQY.B5L2.B1"
    length = _get_element_attr(lhc_interface, quad_name, "l")
    base = _get_effective_strength(lhc_interface, quad_name, "k1")
    integrated_delta = 2e-4

    lhc_interface.set_magnet_strengths({f"{quad_name}.dk1l": integrated_delta})

    # The delta knob is read back verbatim, and the per-metre effective strength
    # shifts by integrated_delta / length.
    assert np.isclose(
        lhc_interface.get_magnet_strengths([f"{quad_name}.dk1l"])[f"{quad_name}.dk1l"],
        integrated_delta,
    )
    assert np.isclose(
        _get_effective_strength(lhc_interface, quad_name, "k1"),
        base + integrated_delta / length,
    )


def test_set_magnet_strengths_bend_moves_closed_orbit(
    lhc_interface: AcceleratorMadInterface,
) -> None:
    """A fixed-bend ``.dk0l`` knob must actually perturb the closed orbit (the bug fix)."""
    bend_name = "MB.C14R2.B1"

    lhc_interface.mad.send("""
local t = twiss {sequence=loaded_sequence, observe=0}
py:send(t:getcol('x'):map(math.abs):max(), true)
""")
    max_x_before = float(lhc_interface.mad.recv())

    lhc_interface.set_magnet_strengths({f"{bend_name}.dk0l": 1e-5})

    lhc_interface.mad.send("""
local t = twiss {sequence=loaded_sequence, observe=0}
py:send(t:getcol('x'):map(math.abs):max(), true)
""")
    max_x_after = float(lhc_interface.mad.recv())

    assert not np.isclose(max_x_after, max_x_before)


def test_set_magnet_strengths_rejects_unknown_suffix(
    lhc_interface: AcceleratorMadInterface,
) -> None:
    """A name that is not a recognised magnet-strength attribute is rejected."""
    with pytest.raises(ValueError, match="must end with one of"):
        lhc_interface.set_magnet_strengths({"MQY.B5L2.B1.bogus": 1.0})


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


def test_quadrupole_knob_updates_use_dknl(
    lhc_interface: AcceleratorMadInterface,
) -> None:
    """Quadrupole dknl should follow the live knob value without mutating base k1."""

    knob_name = "MQ.13R2.B1.dk1l"
    element_name = knob_name.removesuffix(".dk1l")
    absolute_name = f"{element_name}.k1"
    initial_strength_base = lhc_interface.get_base_magnet_strengths([absolute_name])[
        absolute_name
    ]
    initial_strength = lhc_interface.get_magnet_strengths([absolute_name])[
        absolute_name
    ]
    assert np.isclose(initial_strength, initial_strength_base)
    initial_k1 = float(lhc_interface.mad.loaded_sequence[element_name].k1)
    length = float(lhc_interface.mad.loaded_sequence[element_name].l)

    # Before any knob is set, the dknl table should be empty.
    assert lhc_interface.mad.loaded_sequence[element_name].dknl.eval() == []

    step = 1e-4
    lhc_interface.set_magnet_strengths({knob_name: step})

    updated_strength = lhc_interface.get_magnet_strengths([absolute_name])[
        absolute_name
    ]
    updated_strength_base = lhc_interface.get_base_magnet_strengths([absolute_name])[
        absolute_name
    ]
    updated_k1 = float(lhc_interface.mad.loaded_sequence[element_name].k1)
    updated_dknl = float(lhc_interface.mad.loaded_sequence[element_name].dknl[1])

    # dknl is an *integrated* strength (dk1l == delta of knl = k1*l), so a knob
    # value of ``step`` raises the effective per-metre k1 by step/length, not by
    # step. This matches the forward model (a dknl of X is equivalent to k1 += X/l,
    # verified by tune equivalence). The stored dknl equals the knob value exactly
    # and the base k1 is untouched.
    assert np.isclose(updated_strength, initial_strength + step / length)
    assert np.isclose(updated_k1, initial_k1)
    assert np.isclose(updated_strength_base, initial_strength_base)
    assert np.isclose(updated_dknl, step)

    lhc_interface.set_magnet_strengths({absolute_name: initial_strength_base})
    final_strength = lhc_interface.get_magnet_strengths([absolute_name])[absolute_name]
    final_strength_base = lhc_interface.get_base_magnet_strengths([absolute_name])[
        absolute_name
    ]
    final_k1 = float(lhc_interface.mad.loaded_sequence[element_name].k1)
    final_dknl = float(lhc_interface.mad.loaded_sequence[element_name].dknl[1])
    assert np.isclose(final_strength, initial_strength_base)
    assert np.isclose(final_k1, initial_k1)
    assert np.isclose(final_strength_base, initial_strength_base)
    assert np.isclose(final_dknl, 0.0)

    with contextlib.suppress(Exception):
        del lhc_interface
