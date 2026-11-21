# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the package is alpha and the API may change in any release.

## [0.0.1] - Unreleased

### Added
- LHC, PSB and FCC-ee accelerator descriptors.
- `AcceleratorMadInterface`, `AcceleratorErrorsMadInterface`, `KnobMadInterface` and `ModelCreatorMadInterface` for MAD-NG sessions: observation, TWISS, tune matching, AC dipole and AC kickers, orbit correction, magnet strengths and perturbations.
- `make_madx_sequence` (LHC, PSB, SPS) and TFS MAD-NG to MAD-X conversion.
- `create_lhc_model`, `create_psb_model` and `create_fcc_model`.
- `LHC(seq_dir=...)`: mandatory for beam 2 (`-1` for the MAD-X beam-2 sequence, `1` for the beam-4 tracking sequence).
- `create_lhc_model(energy=...)` is the total energy (omc3/MAD-X convention); the MAD-NG model is built at exactly that energy.

### Changed
- `apply_magnet_perturbations(rel_error=None)` is the default: relative errors come from the descriptor's per-family tables; a number overrides them for every magnet.
