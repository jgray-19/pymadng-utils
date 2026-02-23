import pandas as pd
import pytest
import tfs

from pymadng_utils.lhc_model_creator.create_models import create_lhc_model
from pymadng_utils.mad.core_mad_interface import CoreMadInterface


@pytest.fixture
def temp_model_dir(tmp_path):
    """Temporary directory for model creation."""
    return tmp_path / "models"


@pytest.mark.parametrize("beam", [1, 2])
def test_create_lhc_models(beam, temp_model_dir, acc_models_path):
    """Test creating LHC model for the specified beam, mimicking main()."""
    # Create model for the specified beam
    nat_tunes = [0.28, 0.31]
    optics_label = "18cm"
    year = "2025"
    modifiers = "R2025aRP_A18cmC18cmA10mL200cm_Flat.madx"

    model_dir = (
        temp_model_dir / f"model_b{beam}__t{nat_tunes[0]}_{nat_tunes[1]}_{optics_label}"
    )
    drv_tunes = [0.27, 0.322]
    create_lhc_model(
        beam=beam,
        output_dir=model_dir,
        year=year,
        modifiers=modifiers,
        fetch="path",
        path=acc_models_path,
        nat_tunes=nat_tunes,
        drv_tunes=drv_tunes,
    )

    # Check that directory is created
    assert model_dir.exists()

    # Expected files (based on typical omc3 output and our workflow)
    expected_files = [
        "twiss.dat",  # Exported TFS
        f"lhcb{beam}_saved.seq",  # MAD-X sequence
        "job.create_model_nominal.madx",  # MAD-X job file
    ]
    for file in expected_files:
        assert (model_dir / file).exists(), f"Missing {file} in beam {beam} model"

    # Check header origin in twiss.dat
    twiss_file = tfs.read(model_dir / "twiss.dat", index="NAME")
    twiss_acd_file = tfs.read(model_dir / "twiss_ac.dat", index="NAME")

    # Verify the tunes and the driven tunes are correctly set in the twiss files
    assert abs(twiss_file.headers["Q1"] % 1 - nat_tunes[0]) < 1e-6, (
        f"Beam {beam} natural Q1 mismatch: expected {nat_tunes[0]}, got {twiss_file.headers['Q1']}"
    )
    assert abs(twiss_file.headers["Q2"] % 1 - nat_tunes[1]) < 1e-6, (
        f"Beam {beam} natural Q2 mismatch: expected {nat_tunes[1]}, got {twiss_file.headers['Q2']}"
    )
    assert abs(twiss_acd_file.headers["Q1"] % 1 - drv_tunes[0]) < 1e-6, (
        f"Beam {beam} driven Q1 mismatch: expected {drv_tunes[0]}, got {twiss_acd_file.headers['Q1']}"
    )
    assert abs(twiss_acd_file.headers["Q2"] % 1 - drv_tunes[1]) < 1e-6, (
        f"Beam {beam} driven Q2 mismatch: expected {drv_tunes[1]}, got {twiss_acd_file.headers['Q2']}"
    )

    # Origin should be from MAD, not MADX
    assert "MAD" in twiss_file.headers.get("ORIGIN", ""), (
        f"Beam {beam} twiss origin should be MAD"
    )
    assert "MADX" not in twiss_file.headers.get("ORIGIN", ""), (
        f"Beam {beam} twiss origin should not be MADX"
    )

    # Test loading sequence and running twiss with MadCoreInterface
    mad = CoreMadInterface()
    sequence_file = model_dir / f"lhcb{beam}_saved.seq"
    mad.load_sequence(sequence_file, f"lhcb{beam}")
    mad.setup_beam(beam_energy=6800)

    # Run twiss
    mad.observe_elements("IP.")
    twiss_result = mad.run_twiss()

    assert abs(twiss_result.q1 % 1 - nat_tunes[0]) < 1e-6, (
        f"Beam {beam} Q1 mismatch: expected {nat_tunes[0]}, got {twiss_result.q1}"
    )
    assert abs(twiss_result.q2 % 1 - nat_tunes[1]) < 1e-6, (
        f"Beam {beam} Q2 mismatch: expected {nat_tunes[1]}, got {twiss_result.q2}"
    )

    # Check betas at IP1 and IP5
    ip1_data = twiss_result.loc["IP1"]
    ip5_data = twiss_result.loc["IP5"]

    # Assuming units are m, but check ratios.
    ratio_ip1 = ip1_data["beta11"] / ip1_data["beta22"]
    ratio_ip5 = ip5_data["beta11"] / ip5_data["beta22"]

    print(f"Beam {beam} IP1 beta ratio (betx/bety): {ratio_ip1:.2f}")
    print(f"Beam {beam} IP5 beta ratio (betx/bety): {ratio_ip5:.2f}")

    # Roughly 60/18 ≈ 3.33, 18/60 ≈ 0.3
    assert 3.2 < ratio_ip1 < 3.4, f"IP1 betx/bety ratio {ratio_ip1} not around 3.33"
    assert 0.29 < ratio_ip5 < 0.31, f"IP5 betx/bety ratio {ratio_ip5} not around 0.3"

    # Check that twiss.dat matches the run twiss
    # Compare key columns
    mad.unobserve_elements(["IP."])
    mad.observe_elements("BPM")
    twiss_result = mad.run_twiss(coupling=True)
    twiss_result.columns = [
        col.upper() for col in twiss_result.columns
    ]  # Ensure uppercase for comparison
    for col in ["BETX", "BETY", "ALFX", "ALFY", "DX", "DY"]:
        if col in twiss_result.columns and col in twiss_file.columns:
            pd.testing.assert_series_equal(
                twiss_result[col], twiss_file[col], check_names=False, atol=1e-6
            )
