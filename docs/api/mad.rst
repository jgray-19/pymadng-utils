MAD-NG Interfaces
=================

``pymadng_utils.mad`` contains the reusable object model for working with MAD-NG sessions.

Overview
--------

* ``CoreMadInterface`` exposes sequence loading, beam setup, variable management, marker installation, and TWISS execution.
* ``KnobMadInterface`` adds helpers for applying corrector tables and tune-knob files.
* ``AcDipoleMadInterface`` extends the core interface with AC-dipole installation.
* ``ModelCreatorMadInterface`` and ``LhcModelCreatorMadInterface`` specialise the interface stack for model-export workflows.

Package exports
---------------

.. automodule:: pymadng_utils.mad
   :members:
   :undoc-members:
   :show-inheritance:

Core interface
--------------

.. automodule:: pymadng_utils.mad.core_mad_interface
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
