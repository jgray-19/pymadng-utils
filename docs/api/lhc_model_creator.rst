LHC Model Creator
=================

``pymadng_utils.lhc_model_creator`` builds higher-level workflows on top of the lower-level MAD-NG and MAD-X utilities.

Typical workflow
----------------

#. Create or fetch a base LHC model with ``create_lhc_model``.
#. Generate saved MAD-X sequences with ``make_lhc_sequence``.
#. Re-open the model in MAD-NG and export TWISS tables with ``update_model_with_madng``.

Create models
-------------

.. automodule:: pymadng_utils.lhc_model_creator.create_models
   :members:
   :undoc-members:
   :show-inheritance:

MAD-NG update helpers
---------------------

.. automodule:: pymadng_utils.lhc_model_creator.madng_utils
   :members:
   :undoc-members:
   :show-inheritance:

Sequence generation helpers
---------------------------

.. automodule:: pymadng_utils.lhc_model_creator.make_sequence
   :members:
   :undoc-members:
   :show-inheritance:
