Model Creator
=============

``pymadng_utils.model_creator`` builds higher-level workflows on top of the lower-level MAD-NG and MAD-X utilities.

Typical workflow
----------------

#. Create or fetch a base model directory with OMC3.
#. Generate a saved MAD-X sequence with ``pymadng_utils.madx.make_sequence.make_madx_sequence``.
#. Re-open that sequence in MAD-NG and export TWISS tables with ``update_model_with_madng``.

Notes
-----

* ``create_lhc_model`` is the packaged end-to-end workflow for LHC.
* PSB tests currently call ``omc3.model_creator.create_instance_and_model()`` directly and then use the MAD-X and MAD-NG helper layers from this package.
* Sequence generation intentionally expects a real nominal OMC3 job file and now raises on ambiguous layouts instead of guessing from directory names.

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
