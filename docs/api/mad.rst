MAD-NG Interfaces
=================

``pymadng_utils.mad`` contains the reusable object model for working with MAD-NG sessions.

Overview
--------

* ``AcceleratorMadInterface`` exposes sequence loading, beam setup, variable management, marker installation, TWISS execution, magnet perturbations, and orbit correction.
* ``AcceleratorErrorsMadInterface`` is the opt-in variant that applies accelerator-defined startup errors after loading the sequence.
* ``KnobMadInterface`` adds helpers for applying corrector tables and knob files.
* ``ModelCreatorMadInterface`` specialises the interface stack for model-export workflows.

Interface layering
------------------

The MAD interface stack is intentionally split:

* Use ``AcceleratorMadInterface`` when you want a clean loaded machine with no automatic machine-specific error application.
* Use ``AcceleratorErrorsMadInterface`` when the accelerator descriptor provides an ``apply_accelerator_specific_errors`` hook and you want that hook executed automatically.
* Use ``KnobMadInterface`` or ``ModelCreatorMadInterface`` on top when the workflow also needs corrector-file, knob-file, or export helpers.

Practical guidance
------------------

* Start with ``AcceleratorMadInterface`` unless you know you need one of the specialised wrappers.
* Use ``ModelCreatorMadInterface`` indirectly through ``update_model_with_madng`` for model-directory workflows.
* Treat the accelerator descriptor as part of the runtime contract: tune variables, sequence naming, BPM patterns, and AC-dipole placement all come from that object.

Package exports
---------------

.. automodule:: pymadng_utils.mad
   :members:
   :undoc-members:
   :show-inheritance:

Core interface
--------------

.. automodule:: pymadng_utils.mad.accelerator_mad_interface
   :members:
   :undoc-members:
   :show-inheritance:

Knob helpers
------------

.. automodule:: pymadng_utils.mad.knob_mad_interface
   :members:
   :undoc-members:
   :show-inheritance:

Model-creation interfaces
-------------------------

.. automodule:: pymadng_utils.mad.model_creator_mad_interface
   :members:
   :undoc-members:
   :show-inheritance:
