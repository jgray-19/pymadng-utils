"""Corrector deferral of the FCC-ee MAD-X lattice (no MAD-NG)."""

import pytest

from pymadng_utils.model_creator.create_fcc_model import bpms_to_monitors, defer_correctors, slice_sextupoles

LATTICE = """\
kqd = -0.275;
fccee_p_ring: sequence, l=10.0;
hcor_qd0ar.0: kicker, hkick = -0.0, vkick = 0.0, lrad = 0.0, at=2.4;
vcor_qd0ar.0: kicker, hkick = -0.0, vkick = 0.0, lrad = 0.0, at=2.4;
qd0ar.0: quadrupole, l = 0.75, k1 := (kqd), at=2.775;
endsequence;
"""


def test_every_corrector_kick_becomes_its_own_variable():
    text, variables = defer_correctors(LATTICE)
    assert variables == {"hcor_qd0ar.0": "k_hcor_qd0ar.0", "vcor_qd0ar.0": "k_vcor_qd0ar.0"}
    lines = text.splitlines()
    assert "hcor_qd0ar.0: kicker, hkick := k_hcor_qd0ar.0, vkick = 0.0, lrad = 0.0, at=2.4;" in lines
    assert "vcor_qd0ar.0: kicker, hkick = -0.0, vkick := k_vcor_qd0ar.0, lrad = 0.0, at=2.4;" in lines


def test_variables_are_declared_before_the_sequence_and_other_lines_survive():
    text, _ = defer_correctors(LATTICE)
    lines = text.splitlines()
    sequence = lines.index("fccee_p_ring: sequence, l=10.0;")
    assert lines.index("k_hcor_qd0ar.0 = 0.0;") < sequence
    assert "qd0ar.0: quadrupole, l = 0.75, k1 := (kqd), at=2.775;" in lines


def test_text_without_correctors_is_rejected():
    with pytest.raises(ValueError):
        defer_correctors("fccee_p_ring: sequence, l=1.0;\nendsequence;\n")


def test_bpm_markers_become_monitors_and_other_markers_stay():
    text = bpms_to_monitors("bpm_qd0ar.0: marker, at=2.4;\nip.0: marker, at=0.0;\n")
    assert text.splitlines() == ["bpm_qd0ar.0: monitor, at=2.4;", "ip.0: marker, at=0.0;"]


def test_sextupoles_get_three_slices():
    text = slice_sextupoles("sdm1r.0: sextupole, l = 0.6, k2 := (ksd), at=112.5;\nqd0ar.0: quadrupole, l = 0.75, at=2.775;\n")
    assert text.splitlines() == [
        "sdm1r.0: sextupole, l = 0.6, k2 := (ksd), nslice=3, at=112.5;",
        "qd0ar.0: quadrupole, l = 0.75, at=2.775;",
    ]
