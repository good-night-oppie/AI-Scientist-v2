"""Canned BFTS node tree for the deterministic helios replay harness.

Six node records spanning six node-types with two buggy nodes. Each ``code`` string
is a self-contained program (like the single-file scripts BFTS generates) that writes
its artifacts to the current working directory and NOTHING to a print statement --
artifacts are emitted with ``numpy.save`` / raw file writes only, so the Phase-5
cleanliness grep (no added ``print`` calls) stays green.

Determinism: every array is a fixed ``numpy`` constant, and the ``.npy`` on-disk format
carries no timestamp, so ``numpy.save`` is byte-deterministic across runs. This is what
lets the content-addressed snapshot ids be asserted for exact equality.

The two buggy nodes (``n_debug``, ``n_ablation``) each write the SAME array A as their
only file and then crash (``sys.exit(1)`` / ``raise``) AFTER the file is fully flushed.
Their post-exec working dirs are therefore byte-identical, which must yield the IDENTICAL
snapshot id -- the content-addressing / provenance-integrity proof (AC9). Crucially,
today both would archive nothing (``exp_results_dir=None``) and be lost to the exit-time
rmtree; the hook captures them anyway.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NodeRecord:
    id: str
    node_type: str
    is_buggy: bool
    code: str


# Save array A (int64 3x4) as the sole artifact. Shared verbatim by the draft node and
# the two buggy nodes so their `.npy` bytes are identical.
_SAVE_A = (
    "import numpy as np\n"
    'np.save("experiment_data.npy", np.arange(12, dtype="int64").reshape(3, 4))\n'
)

# Fixed PNG-ish bytes (deterministic; content is irrelevant, only that it is stable).
_PNG_DRAFT = (
    'with open("figure.png", "wb") as fh:\n'
    '    fh.write(b"\\x89PNG\\r\\n\\x1a\\nFIXED-FIGURE-BYTES-DRAFT")\n'
)
_PNG_IMPROVE = (
    'with open("figure.png", "wb") as fh:\n'
    '    fh.write(b"\\x89PNG\\r\\n\\x1a\\nFIXED-FIGURE-BYTES-IMPROVE")\n'
)


FIXTURE_TREE = [
    NodeRecord(
        id="n_draft",
        node_type="draft",
        is_buggy=False,
        code=_SAVE_A + _PNG_DRAFT,
    ),
    NodeRecord(
        id="n_debug",
        node_type="debug",
        is_buggy=True,
        # Produced its data file, THEN crashed non-zero -- the reproducibility black hole.
        code=_SAVE_A + "import sys\nsys.exit(1)\n",
    ),
    NodeRecord(
        id="n_improve",
        node_type="improve",
        is_buggy=False,
        code=(
            "import numpy as np\n"
            'np.save("experiment_data.npy", np.full((4,), 2.5, dtype="float64"))\n'
        )
        + _PNG_IMPROVE,
    ),
    NodeRecord(
        id="n_hparam",
        node_type="hyperparam",
        is_buggy=False,
        code=(
            "import numpy as np\n"
            'np.save("experiment_data.npy", '
            'np.array([[1, 2, 3], [4, 5, 6]], dtype="int32"))\n'
        ),
    ),
    NodeRecord(
        id="n_ablation",
        node_type="ablation",
        is_buggy=True,
        # Byte-identical data file to n_debug, then raises -> identical snapshot id.
        code=_SAVE_A + 'raise RuntimeError("ablation crash after saving data")\n',
    ),
    NodeRecord(
        id="n_seed",
        node_type="seed",
        is_buggy=False,
        code=(
            "import numpy as np\n"
            'np.save("experiment_data.npy", np.arange(9, dtype="float32").reshape(3, 3))\n'
        ),
    ),
]
