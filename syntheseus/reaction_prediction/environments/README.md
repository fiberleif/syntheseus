# Single-step Model Environments

Every single-step model may require a different environment and set of dependencies.
Here we outline the steps to set up an environment for each of the supported models, which can be then used to run single-step model evaluation or multi-step search.

## Basic setup

All models apart from GLN can be set up using a shared base `conda` environment extended with a few model-specific dependencies. The general workflow is:

```bash
conda env create -f environment_shared.yml  # Create the shared environment.
conda activate syntheseus-single-step       # Activate the environment.
pip install -e ../../../                    # Install `syntheseus`.
source setup_[MODEL_NAME].sh                # Run the extra setup commands.
```

If you wish to use several models, it's enough to create the environment once and run all the corresponding setup scripts.
However, note that RetroKNN depends on LocalRetro, so if you want to use both, it is enough to run just `setup_retro_knn.sh`.

In `environment_shared.yml` and `setup_local_retro.sh` we pinned the CUDA version (to 11.3) for reproducibility.
If you want to use a different one, make sure to edit these two files accordingly.

The GLN model is not compatible with the others, currently requiring a specialized environment creation which includes building `rdkit` from source.
We packaged all the necessary steps into a Docker environment defined in `gln/Dockerfile`.

## Back-translation

In `reaction_prediction/cli/eval.py` a forward model may be used for computing back-translation (round-trip) accuracy.
Currently, Chemformer is the only supported forward model.

To evaluate a particular model with back-translation computed using Chemformer, simply set up an environment for that model and then run `setup_chemformer.sh` on top.
