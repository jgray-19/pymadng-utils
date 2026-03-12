# pymadng-utils

[![codecov](https://codecov.io/gh/jgray-19/pymadng-utils/graph/badge.svg?token=L1EV8MDM6M)](https://codecov.io/gh/jgray-19/pymadng-utils)

General-purpose utilities based on MAD-NG via `pymadng`, including model creation helpers migrated from `sgd-magnet-tuner`.

## Layout

- `src/pymadng_utils/mad`: MAD-NG interface classes
- `src/pymadng_utils/physics`: MAD-NG-related physics helpers
- `src/pymadng_utils/model_creator`: model creation utilities (MAD-X/MAD-NG/TFS)
- `tests/mad`: interface tests
- `tests/physics/test_deltap.py`: physics conversion tests
- `tests/data`: sequence and knob fixtures for tests

## Run tests

```bash
pip install -e .[test]
pytest tests/physics/test_deltap.py tests/mad/test_base_interface.py
```
