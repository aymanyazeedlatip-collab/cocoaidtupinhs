"""COCO-AID package initialization.

Limit native numerical libraries before NumPy/scikit-learn load. This prevents
small simulations from spawning dozens of BLAS threads on ordinary laptops and
in test runners, which can make the application appear frozen.
"""
from __future__ import annotations

import os

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ.setdefault(_name, "1")
