Usage
=====

Installation
------------

Install the core runtime or an editable checkout with model dependencies:

.. code-block:: console

   python -m pip install .
   python -m pip install -e '.[model]'

The core install needs only ``numpy``, ``pandas``, ``tfs-pandas`` and ``pymadng>=0.10.0``. The ``model`` extra adds ``cpymad`` and ``omc3``, which ``pymadng_utils.madx.make_sequence`` and ``pymadng_utils.model_creator.create_models`` import. The ``test`` extra adds pytest and the model dependencies, ``dev`` adds ``pre-commit`` and ``ruff``, and ``docs`` adds Sphinx and the Furo theme.

MAD-NG compatibility
--------------------

``pymadng`` bundles its own MAD-NG binary and the off-momentum closed-orbit tolerances here (``cotol=1e-11``) are tuned against it, so results can differ in the last digits, and the closed-orbit search can fail to converge, with another MAD-NG build. The suite is validated with ``pymadng>=0.10.0`` on Linux; the output-suppression script uses POSIX file descriptors.

Run MAD-NG on a saved sequence
------------------------------

An accelerator descriptor supplies the sequence name, particle, kinetic energy, BPM pattern, tune knobs, and AC-dipole element. Creating the interface immediately loads the sequence and sets its beam.

.. code-block:: python

   from pathlib import Path

   from pymadng_utils.accelerators import LHC
   from pymadng_utils.mad import AcceleratorMadInterface

   accelerator = LHC(
       beam=1,
       sequence_file=Path("lhcb1_saved.seq"),
       kinetic_energy=6800.0,
   )

   with AcceleratorMadInterface(accelerator) as interface:
       interface.observe()
       twiss = interface.run_twiss(coupling=True)
       print(twiss.headers["q1"], twiss.headers["q2"])

For ``beam=2`` ``seq_dir`` is mandatory: ``-1`` runs the MAD-X beam-2 sequence backwards, ``1`` is the forward beam-4 tracking sequence (also named ``lhcb2``). ``kinetic_energy`` is expressed in GeV. The interface adds the particle rest mass before configuring MAD-NG's total beam energy. The sequence is translated on every load; ``load_sequence(cache_translation=True)`` writes a sibling ``.mad`` cache, which is unsafe for parallel loaders of the same sequence.

``run_twiss`` observes the selected elements by default and returns a DataFrame indexed by element name. Its ``pt`` convenience keyword uses MAD-NG's longitudinal coordinate directly and cannot be combined with ``X0`` or ``deltap``. A ``deltap`` given without an explicit ``X0`` is converted to ``pt`` by ``MAD.gphys.dp2pt`` on the loaded sequence's beam and seeded through that same path, so ``deltap=dp``, ``pt=interface.dp2pt(dp)``, and MAD-NG's native ``twiss{deltap=dp}`` are bit-identical. The conversions are not mutual inverses to the last bit, so convert once rather than round-tripping.

Machine descriptors
-------------------

``LHC`` requires ``beam=1`` or ``beam=2``. Its defaults are 6800 GeV kinetic energy, the ``^BPM.*$`` observation pattern, the operational tune knobs selected by ``tune_knobs_suffix="_op"``, and integer tunes ``(62, 60)``. ``FCC`` is the FCC-ee LCC single ring (``mode`` z/w/h/t, electron by default). ``PSB`` accepts rings 1--4 and defaults to 0.160 GeV; it can infer the ring from a sequence filename containing ``psbN``, otherwise ``ring=`` is required. There is no SPS runtime descriptor. ``FCC`` has no AC dipole.

Interface classes
-----------------

* ``AcceleratorMadInterface`` -- sequence/beam setup and the core MAD-NG operations.
* ``AcceleratorErrorsMadInterface`` -- the core interface plus the descriptor's startup-error hook.
* ``KnobMadInterface`` -- the core interface plus knob and corrector-table loading.
* ``ModelCreatorMadInterface`` -- tune matching and model-table export.

The first three are exported by ``pymadng_utils.mad``; ``ModelCreatorMadInterface`` is imported from ``pymadng_utils.mad.model_creator_mad_interface``.

``match_tunes(target_qx, target_qy)`` varies the descriptor's two tune knobs until the
tunes are reached (fractional targets use the descriptor's integer tunes; targets of 1 or
more are taken as total tunes). The knobs are TPSA parameters during the match, so the
tune Jacobian is exact and a match takes about three twiss calls
(``mad_scripts/match_tunes.mad``). ``deltap=`` or ``pt=`` match at that momentum.

Common operations are ``observe``, ``observe_element`` and ``observe_elements``;
``run_twiss``; ``match_tunes`` over the descriptor's two tune variables;
``set_magnet_strengths``, ``get_magnet_strengths`` and ``get_base_magnet_strengths``;
``apply_magnet_perturbations`` for the descriptor's dipole, quadrupole and sextupole
families; ``perform_orbit_correction``; ``install_ac_dipole`` and ``insert_acd_markers``;
``install_ac_kickers``; and ``cycle_sequence``.

``apply_magnet_perturbations`` takes its relative errors from the descriptor's per-family tables (for the LHC, quadrupoles use ``QUAD_ERROR_TABLE`` by name prefix and others are untouched); a ``rel_error`` argument overrides the tables for every selected magnet.

Magnet-strength keys are ``ELEMENT.attribute``, for example ``MQ.12L1.B1.k1``,
``MB.A12L1.B1.dk0l`` or ``MQ.12L1.B1.dx``. Multipoles cover normal and skew orders 0--2,
either as absolute ``kN``/``kNs`` or integrated delta ``dkNl``/``dkNsl`` values; ``dx``,
``dy`` and ``kick`` are also accepted. Multipole changes are routed through MAD-NG's
deferred ``dknl``/``dksl`` tables.

``KnobMadInterface`` adds ``observe_bpms(pattern, bad_bpms=...)``, which observes a BPM
pattern and then unobserves the listed bad BPMs; ``set_knobs``, which reads a
tab-delimited ``name<TAB>value`` file; and ``set_corrector_strengths``, which first tries
to read its input as a TFS corrector table and falls back to that knob format.

AC kickers
----------

``install_ac_kickers(kicks, freqs)`` installs four thin flattop kickers at the position of
the accelerator's AC-dipole element: ``hackicker_a/b`` and ``vackicker_a/b``, returned as
the tuple ``AC_KICKERS``. The AC-dipole element itself stays in the sequence and must
already be thin, otherwise a ``RuntimeError`` is raised; ``insert_acd_markers()`` thins it.
The ``a`` kicker has lag 0 and the ``b`` kicker lag 1/4, so in each plane the kick is
``0.3 / pc (a sin(phi) + b cos(phi))`` with ``phi = 2 pi turn freq`` and ``turn`` the MAD-NG
turn counter. The kick is therefore linear in the four volts, which makes them usable as
fit knobs. ``kicks`` are the initial volts ``(a_x, b_x, a_y, b_y)`` and ``freqs`` the
horizontal and vertical drive tunes.

``pymadng_utils.mad.ac_kickers`` provides functions on a ``MAD`` instance to drive them
after installation:

* ``set_ac_kicker_freqs(mad, freqs)`` sets the drive tunes;
* ``bind_ac_kicker_volts(mad, variables)`` makes each volt follow
  ``loaded_sequence[variable]`` (a sequence variable, not a ``MADX`` variable), so the
  volts can be varied as knobs;
* ``shift_ac_kicker_phase(mad, turn_offset)`` makes MAD turn ``t`` act as turn
  ``t + turn_offset`` of the measurement; the first MAD pass is turn 0.

Export a reusable MAD-X sequence
--------------------------------

``make_madx_sequence`` consumes an existing OMC3 nominal model directory:

.. code-block:: python

   from pathlib import Path
   from pymadng_utils.madx.make_sequence import make_madx_sequence

   sequence_file = make_madx_sequence(Path("model"))

The directory must contain ``job.create_model_nominal.madx`` with an explicit, unambiguous ``use, sequence=...;`` statement:

* ``lhcb1`` or ``lhcb2`` for LHC;
* ``psb1`` through ``psb4`` for PSB; or
* ``sps`` for SPS.

LHC export also requires OMC3's ``! LHC year ...`` header. The helper deliberately raises for missing or ambiguous metadata instead of guessing from a directory name.

``seq_outdir`` selects another output directory. ``beam4=True`` is valid only for LHC beam 2. ``post_optics_madx_files`` is available for LHC and SPS, but not PSB.

Regenerate model tables with MAD-NG
-----------------------------------

Use ``update_model_with_madng`` after producing a saved sequence:

.. code-block:: python

   from pathlib import Path

   from pymadng_utils.accelerators import PSB
   from pymadng_utils.madx.make_sequence import make_madx_sequence
   from pymadng_utils.model_creator.madng_utils import update_model_with_madng

   model_dir = Path("psb-model")
   sequence_file = make_madx_sequence(model_dir)

   update_model_with_madng(
       accelerator=PSB(sequence_file=sequence_file, ring=3),
       model_dir=model_dir,
       tunes=[0.17, 0.225],
       drv_tunes=[0.162, 0.232],
       deltap=0.0,
   )

The workflow matches the fractional natural tunes and writes:

* ``twiss.dat`` for observed natural optics;
* ``twiss_elements.dat`` for all non-drift natural-optics elements; and
* ``twiss_ac.dat`` after installing the AC dipole when driven tunes are supplied.

By default these files are converted in place to uppercase MAD-X/OMC3 names. Set ``convert_to_madx=False`` to retain MAD-NG column names. With ``tunes=None``, the target tunes are read from an existing ``twiss.dat``.

Create an LHC or PSB model
--------------------------

``pymadng_utils.model_creator.create_models`` has two end-to-end creators. Both run nominal OMC3 creation, export the saved sequence, and regenerate the TWISS files with MAD-NG:

* ``create_lhc_model(beam, output_dir, year, ...)`` uses beam 4 for beam 2. ``nat_tunes`` defaults to ``(0.28, 0.31)`` and ``drv_tunes`` to ``(0.27, 0.322)``; ``drv_tunes=None`` skips the AC dipole. ``energy`` (default 6800) is the *total* beam energy in GeV, as in omc3 and MAD-X; the MAD-NG descriptor is built with ``energy - PROTON_MASS_GEV`` as kinetic energy.
* ``create_psb_model(ring, output_dir, year, ...)`` takes ring 1--4, ``nat_tunes`` (default ``(0.17, 0.225)``), optional ``drv_tunes``, ``kinetic_energy``, ``dpp``, ``cycle_point``, ``str_file`` and ``scenario``. ``update_with_madng=False`` stops after the sequence export, for callers that run their own MAD-NG step.

Prepare the FCC-ee lattice
--------------------------

``pymadng_utils.model_creator.create_fcc_model.create_fcc_model(lattice_dir, output_file)`` rewrites an FCC-ee LCC MAD-X file for LOCO studies: ``bpm_*`` markers become monitors, sextupoles get three slices, and every ``hcor_*``/``vcor_*`` kicker takes its kick from a MAD-X variable ``k_<name>`` (declared at zero). It returns ``{corrector name: variable}``. It needs no MAD-X or OMC3 and uses only the standard library.

Resource management
-------------------

MAD-NG interfaces own a subprocess. Prefer a ``with`` statement; otherwise call ``close``. Model workflows write into their target directories, and TFS conversion helpers overwrite the supplied files in place.

Momentum conversions without a MAD-NG session
---------------------------------------------

``pymadng_utils.physics`` converts ``dp/p`` and MAD-NG ``pt`` for a known ``beta0``:

.. code-block:: pycon

   >>> from pymadng_utils.physics import beta_from_energy, dp2pt
   >>> beta0 = beta_from_energy(0.93827208816 + 0.160)  # PSB flat bottom, total energy in GeV
   >>> round(dp2pt(1e-3, beta0), 8)
   0.00051994
