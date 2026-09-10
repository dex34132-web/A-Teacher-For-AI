# Experiments

Exploratory research and prototype implementations for the AI Learning Engine.

## Structure

Each experiment should live in its own subdirectory with:

- A `README.md` describing the hypothesis and setup
- A script or notebook that runs the experiment
- Results stored in a `results/` directory (git-ignored)

## Guidelines

- Experiments are **not** part of the installed package.
- Keep experiments self-contained; they may depend on unstable APIs.
- Document findings in `docs/experiments/` after a successful run.
