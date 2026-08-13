Usage
=====

Installation
------------

Install the core runtime or an editable checkout with model dependencies:

.. code-block:: console

   python -m pip install .
   python -m pip install -e '.[model]'

The ``test`` extra adds pytest and the model dependencies. The ``docs`` extra adds Sphinx and the Read the Docs theme.

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

``kinetic_energy`` is expressed in GeV. The interface adds the particle rest mass before configuring MAD-NG's total beam energy. Loading also creates or reuses a translated ``.mad`` cache next to the input sequence.

``run_twiss`` observes the selected elements by default and returns a DataFrame indexed by element name. Its ``pt`` convenience keyword uses MAD-NG's longitudinal coordinate directly and cannot be combined with ``X0`` or ``deltap``. A ``deltap`` given without an explicit ``X0`` is converted to ``pt`` by ``MAD.gphys.dp2pt`` on the loaded sequence's beam and seeded through that same path, so ``deltap=dp``, ``pt=interface.dp2pt(dp)``, and MAD-NG's native ``twiss{deltap=dp}`` are bit-identical. The conversions are not mutual inverses to the last bit, so convert once rather than round-tripping.

Machine descriptors
-------------------

``LHC`` requires ``beam=1`` or ``beam=2``. Its defaults are 6800 GeV kinetic energy, the ``^BPM.*$`` observation pattern, the operational tune knobs selected by ``tune_knobs_suffix="_op"``, and integer tunes ``(62, 60)``. ``PSB`` accepts rings 1--4 and defaults to 0.160 GeV; it can infer the ring from a sequence filename containing ``psbN``, otherwise ``ring=`` is required. There is no SPS runtime descriptor.

Interface classes
-----------------

* ``AcceleratorMadInterface`` -- sequence/beam setup and the core MAD-NG operations.
* ``AcceleratorErrorsMadInterface`` -- the core interface plus the descriptor's startup-error hook.
* ``KnobMadInterface`` -- the core interface plus knob and corrector-table loading.
* ``ModelCreatorMadInterface`` -- tune matching and model-table export.

The first three are exported by ``pymadng_utils.mad``; ``ModelCreatorMadInterface`` is imported from ``pymadng_utils.mad.model_creator_mad_interface``.

Common operations are ``observe``, ``observe_element`` and ``observe_elements``;
``run_twiss``; ``match_tunes`` over the descriptor's two tune variables;
``set_magnet_strengths``, ``get_magnet_strengths`` and ``get_base_magnet_strengths``;
``apply_magnet_perturbations`` for the descriptor's dipole, quadrupole and sextupole
families; ``perform_orbit_correction``; ``install_ac_dipole`` and ``insert_acd_markers``;
and ``cycle_sequence``.

Magnet-strength keys are ``ELEMENT.attribute``, for example ``MQ.12L1.B1.k1``,
``MB.A12L1.B1.dk0l`` or ``MQ.12L1.B1.dx``. Multipoles cover normal and skew orders 0--2,
either as absolute ``kN``/``kNs`` or integrated delta ``dkNl``/``dkNsl`` values; ``dx``,
``dy`` and ``kick`` are also accepted. Multipole changes are routed through MAD-NG's
deferred ``dknl``/``dksl`` tables.

``KnobMadInterface`` adds ``observe_bpms(pattern, bad_bpms=...)``, which observes a BPM
pattern and then unobserves the listed bad BPMs; ``set_knobs``, which reads a
tab-delimited ``name<TAB>value`` file; and ``set_corrector_strengths``, which first tries
to read its input as a TFS corrector table and falls back to that knob format.

Export a reusable MAD-X sequence
--------------------------------

``make_madx_sequence`` consumes an existing OMC3 nominal model directory:

.. code-block:: python

   from pathlib import Path
   from pymadng_utils.madx import make_madx_sequence

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
   from pymadng_utils.madx import make_madx_sequence
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

Create an LHC model
-------------------

``pymadng_utils.model_creator.create_models.create_lhc_model`` is the only packaged end-to-end creator. It runs nominal OMC3 creation, exports the saved sequence (using beam 4 for beam 2), and regenerates the TWISS files with MAD-NG. PSB workflows compose OMC3, ``make_madx_sequence``, and ``update_model_with_madng`` explicitly.

Resource management
-------------------

MAD-NG interfaces own a subprocess. Prefer a ``with`` statement; otherwise call ``close``. Model workflows write into their target directories, and TFS conversion helpers overwrite the supplied files in place.
