Model Creator
=============

``pymadng_utils.model_creator`` builds higher-level workflows on top of the lower-level MAD-NG and MAD-X utilities.

Typical workflow
----------------

#. Create or fetch a base model with ``create_lhc_model``.
#. Generate saved MAD-X sequences with the helpers in ``pymadng_utils.madx.make_sequence``.
#. Re-open the model in MAD-NG and export TWISS tables with ``update_model_with_madng``.

Create models
-------------

.. automodule:: pymadng_utils.model_creator.create_models
   :members:
   :undoc-members:
   :show-inheritance:

MAD-NG update helpers
---------------------

.. automodule:: pymadng_utils.model_creator.madng_utils
   :members:
   :undoc-members:
   :show-inheritance:

Sequence generation helpers
---------------------------

Sequence generation now lives in ``pymadng_utils.madx.make_sequence`` and is documented in the MAD-X section.
