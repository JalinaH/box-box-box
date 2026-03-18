# Box Box Box - Solution README

## Overview

This repository now documents the implemented prediction solution, not the original challenge brief.

The solution uses a deterministic simulation model with a train-and-freeze workflow:

1. Learn model coefficients from historical races.
2. Freeze coefficients into a JSON file.
3. Run fast inference by loading frozen coefficients once at startup.

## Solution Components

- `solution/race_simulator.py`
  Runtime predictor (stdin -> stdout JSON).

- `solution/train_coefficients.py`
  Coefficient trainer using historical race data.

- `solution/frozen_coefficients.json`
  Frozen model parameters used by runtime inference.

- `solution/run_command.txt`
  Command used by the test runner.

## Modeling Approach

The simulator computes each driver total race time lap-by-lap with:

1. Base lap time from race config.
2. Compound base offset.
3. Tire degradation using:
   - linear wear term
   - quadratic wear term
4. Global temperature factor and compound-specific temperature multipliers.
5. Per-track degradation multipliers.
6. Optional per-track compound base addends.
7. Optional per-track cliff-age adjustments.
8. Fresh-tire warmup adjustment on the first lap of each stint.
9. Pit lane time penalty with per-track multiplier.

Drivers are ranked by total simulated race time.

## Coefficient Loading

`solution/race_simulator.py` loads `solution/frozen_coefficients.json` at import time.

The loader is backward compatible:

1. Validates required keys.
2. Fills optional/new keys with defaults when missing.
3. Falls back to built-in defaults if the frozen file is missing or invalid.

## Training Workflow

Train coefficients from historical races:

```bash
python3 solution/train_coefficients.py \
	--iterations 4000 \
	--objective hybrid \
	--seed 42
```

Common options:

- `--objective`:
  `exact`, `pairwise`, or `hybrid`.

- `--max-files`:
  Limit number of historical files for faster experimentation.

- `--max-races`:
  Limit total loaded races.

- `--valid-fraction`:
  Validation split ratio.

- `--output`:
  Custom output path for frozen coefficients.

The default output path is `solution/frozen_coefficients.json`.

## Inference Usage

Run on one input file:

```bash
python3 solution/race_simulator.py < data/test_cases/inputs/test_001.json
```

Run the full local evaluator:

```bash
./test_runner.sh
```

## Implementation Notes

1. Prediction is deterministic (no randomness at inference time).
2. The simulator does not read expected output files during inference.
3. Runtime cost is low because all model parameters are pre-frozen.

## Reference Docs

- `PROBLEM_STATEMENT.md`
- `SUBMISSION_GUIDE.md`
- `docs/data_format.md`
- `docs/regulations.md`
- `docs/faq.md`
