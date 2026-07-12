#!/usr/bin/env python3
"""Phase 7 warm-start measurement + failure-mode harness (deterministic replay).

WHY A HARNESS, NOT A LIVE RUN
-----------------------------
This host has no GPU, no torch and no LLM keys, so a real BFTS run is impossible
(THINKING.md:130-134). Evidence therefore comes from a deterministic replay whose
"node code" is CANNED -- an honest boundary stated in every emitted artifact. What is
under test is NOT an LLM: it is the warm-start MECHANISM
(``helios_store.maybe_warm_start`` -> real ``helios materialize`` from a HEAD-built
binary) plus the two *prompt embodiments* (a reuse-aware script vs a regenerate-always
control), so the numbers below measure exactly the thing this phase ships.

The canned scripts have a genuinely expensive, genuinely cacheable prep step (build a
>=64 MB float64 array via a numpy compute loop tuned to >= ``--prep-seconds`` wall-clock)
-- a faithful stand-in for the dataset download / preprocess the real codegen prompt
permits and that today is repeated across ~250 nodes.

ARMS (all use the real store, HEAD-pinned binary, HELIOS_STORE_DIR outside any workspace,
flock via the Phase-2 wrapper)
  1. PARENT      run reuse-aware in fresh dir P (cache absent) -> prep runs -> commit -> sid
  2. WARM child  fresh empty Cw; maybe_warm_start materializes the cache; reuse-aware ->
                 prep SKIPPED -> warm_seconds
  3. COLD child  fresh empty Cc; NO warm-start; reuse-aware -> prep runs -> cold_seconds
  4. IGNORE ctrl fresh empty Ci; cache materialized; regenerate-always script -> prep runs
                 ANYWAY -> ignore_seconds (isolates the prompt change)
  + DRAFT (parent=None) and BUGGY-parent guards -> cache absent (no materialize)
  + SUBTREE-POISON: wrong-but-valid parent cache; ON -> grandchild reuses it (propagates);
                    OFF -> grandchild recomputes correct bytes
  + TORN snapshot: truncated .npy materialized; bare np.load RAISES (risk real) but the
                    reuse-aware try/except regenerates a clean experiment_data.npy (mitigated)

HONESTY GATE
------------
speedup = cold_seconds / warm_seconds is a real ``time.perf_counter`` measurement, and the
emitted ``WARMSTART_VERDICT`` is ``BENEFIT`` iff speedup >= 1.5 else ``NO_BENEFIT``. A
``NO_BENEFIT`` result is a VALID outcome -- the harness measures and reports the number, it
never manufactures a win, and it never asserts an inequality. The synthetic speedup may NOT
be read as evidence about the REAL BFTS workload; ``cold_vs_warm.md`` says so explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ai_scientist.treesearch.helios_store import (  # noqa: E402
    HeliosStore,
    maybe_warm_start,
)

# 8.5M float64 = 68 MB (> the 64 MB floor); fixed so bytes are reproducible.
_N = 8_500_000
_SPEEDUP_BENEFIT_THRESHOLD = 1.5

# The canned node "code". Reuse-aware EMBODIES the Phase-7 reuse prompt (check cache ->
# validate -> reuse, else regenerate). Ignore is the control (regenerate always). Both
# operate in cwd; the harness sets cwd to the prepared per-node dir.
_CANNED_SCRIPT = r'''
import os, sys
import numpy as np

N = int(os.environ["HARNESS_N"])
ITERS = int(os.environ["HARNESS_ITERS"])
MODE = os.environ["HARNESS_MODE"]            # "reuse" (reuse-aware) | "ignore" (control)
wd = os.getcwd()
cache = os.path.join(wd, "preprocessed.npy")


def rebuild():
    """Expensive, DETERMINISTIC prep: fixed ITERS of a numpy transform over an N-vector.

    Deterministic in (N, ITERS) so the subtree-poison hash comparison is exact; expensive
    because ITERS is calibrated to >= --prep-seconds of wall-clock in the parent process.
    """
    a = np.arange(N, dtype="float64")
    for _ in range(ITERS):
        a = np.sin(a) + np.cos(a) * 0.5 + 1.0
    np.save(cache, a)
    return a


reused = False
if MODE == "reuse" and os.path.exists(cache):
    # Warm-start reuse path with validate-then-regenerate (also the torn-.npy mitigation).
    try:
        d = np.load(cache, allow_pickle=False)
        assert d.shape == (N,)                # shape / sanity check
        reused = True
    except Exception:
        rebuild()                             # corrupt/torn cache -> recompute, never crash
else:
    rebuild()

data = np.load(cache, allow_pickle=False)     # cheap downstream step
np.save(os.path.join(wd, "experiment_data.npy"),
        np.array([float(data.mean()), float(data.std()), float(data.shape[0])]))
with open(os.path.join(wd, "reused.flag"), "w") as fh:
    fh.write("1" if reused else "0")
'''


def _sha256(path):
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _fresh_empty_dir(root, name):
    """A brand-new empty dir (materialize requires empty; Phase-6 dirs are fresh)."""
    d = os.path.join(root, name)
    os.makedirs(d, exist_ok=False)
    return d


def _write_script(root):
    p = os.path.join(root, "node_code.py")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(_CANNED_SCRIPT)
    return p


def _run_script(script, work_dir, iters, mode):
    """Run the canned script in ``work_dir``; return wall-clock seconds (perf_counter)."""
    env = os.environ.copy()
    env["HARNESS_N"] = str(_N)
    env["HARNESS_ITERS"] = str(iters)
    env["HARNESS_MODE"] = mode
    t0 = time.perf_counter()
    cp = subprocess.run(
        [sys.executable, script], cwd=work_dir, env=env, capture_output=True, text=True
    )
    dt = time.perf_counter() - t0
    if cp.returncode != 0:
        raise SystemExit(
            "canned script failed (mode=%s rc=%d): %s"
            % (mode, cp.returncode, cp.stderr)
        )
    return dt


def _calibrate_iters(prep_seconds):
    """Pick a fixed ITERS so one rebuild takes >= prep_seconds on THIS host.

    Fixed within a run => deterministic script output (needed for the poison hash test),
    while still expensive => the timing arms have a real, cacheable prep to skip.
    """
    a = np.arange(_N, dtype="float64")
    t0 = time.perf_counter()
    probe = 3
    for _ in range(probe):
        a = np.sin(a) + np.cos(a) * 0.5 + 1.0
    per_iter = max((time.perf_counter() - t0) / probe, 1e-6)
    return max(1, int(math.ceil(prep_seconds / per_iter)))


def _cfg(binary, store_dir, *, warm_start):
    return SimpleNamespace(
        helios=SimpleNamespace(
            enabled=True,
            warm_start=warm_start,
            binary_path=binary,
            store_dir=store_dir,
            lock_file=store_dir.rstrip("/") + ".flock",
        )
    )


def _resolve_binary():
    binary = os.environ.get("HELIOS_CLI_BIN")
    if not binary:
        cand = os.path.join(_REPO_ROOT, ".supergoal", "bin", "helios")
        if os.path.isfile(cand):
            binary = cand
    if not binary or not (os.path.isfile(binary) and os.access(binary, os.X_OK)):
        raise SystemExit(
            "HELIOS_CLI_BIN not set to an executable helios built from HEAD; got %r"
            % binary
        )
    return os.path.abspath(binary)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prep-seconds", type=float, default=3.0)
    ap.add_argument("--out", required=True, help="evidence dir (M7)")
    args = ap.parse_args(argv)

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    binary = _resolve_binary()

    scratch = tempfile.mkdtemp(prefix="warm_start_harness_")
    store_dir = os.path.join(scratch, "helios_store")  # OUTSIDE any workspace_dir
    store = HeliosStore(binary, store_dir)
    cfg_on = _cfg(binary, store_dir, warm_start=True)
    cfg_off = _cfg(binary, store_dir, warm_start=False)

    script = _write_script(scratch)
    iters = _calibrate_iters(args.prep_seconds)

    # ============================ TIMING ARMS ================================= #
    # Arm 1: PARENT — cache absent -> prep runs -> commit the working dir.
    p_dir = _fresh_empty_dir(scratch, "P")
    _run_script(script, p_dir, iters, "reuse")
    assert os.path.exists(os.path.join(p_dir, "preprocessed.npy"))
    parent_sid = store.snapshot(p_dir)
    parent_node = SimpleNamespace(is_buggy=False, snapshot_id=parent_sid)

    # Arm 2: WARM child — materialize parent cache into a FRESH EMPTY dir, then exec.
    cw = _fresh_empty_dir(scratch, "Cw")
    warm_state = maybe_warm_start(cfg_on, parent_node, cw)
    warm_cache_present_before = os.path.exists(os.path.join(cw, "preprocessed.npy"))
    warm_seconds = _run_script(script, cw, iters, "reuse")
    warm_reused = _read_flag(cw)

    # Arm 3: COLD child — no warm-start; cache absent before exec.
    cc = _fresh_empty_dir(scratch, "Cc")
    cold_cache_present_before = os.path.exists(os.path.join(cc, "preprocessed.npy"))
    cold_seconds = _run_script(script, cc, iters, "reuse")
    cold_reused = _read_flag(cc)

    # Arm 4: IGNORE control — cache materialized, but regenerate-always prompt -> prep runs.
    ci = _fresh_empty_dir(scratch, "Ci")
    maybe_warm_start(cfg_on, parent_node, ci)
    ignore_cache_present_before = os.path.exists(os.path.join(ci, "preprocessed.npy"))
    ignore_seconds = _run_script(script, ci, iters, "ignore")
    ignore_reused = _read_flag(ci)

    # DRAFT + BUGGY guards — no parent filesystem is ever inherited.
    cd = _fresh_empty_dir(scratch, "Cd")
    draft_state = maybe_warm_start(cfg_on, None, cd)
    draft_cache_present = os.path.exists(os.path.join(cd, "preprocessed.npy"))

    cb = _fresh_empty_dir(scratch, "Cb")
    buggy_parent = SimpleNamespace(is_buggy=True, snapshot_id=parent_sid)
    buggy_state = maybe_warm_start(cfg_on, buggy_parent, cb)
    buggy_cache_present = os.path.exists(os.path.join(cb, "preprocessed.npy"))
    buggy_dir_empty = os.listdir(cb) == []

    # ========================= DERIVED NUMBERS =============================== #
    speedup = cold_seconds / warm_seconds
    prompt_effect = ignore_seconds / warm_seconds
    verdict = "BENEFIT" if speedup >= _SPEEDUP_BENEFIT_THRESHOLD else "NO_BENEFIT"

    # ========================= FAILURE MODES ================================= #
    poison = _run_subtree_poison(
        scratch, store, binary, store_dir, cfg_on, cfg_off, iters
    )
    torn = _run_torn_snapshot(scratch, store, cfg_on, iters)

    # ============================ ASSERTIONS ================================= #
    # AC5: warm has cache before exec; cold/draft/buggy do NOT.
    assert warm_state == "warm", warm_state
    assert warm_cache_present_before, "AC5: WARM child missing cache before exec"
    assert not cold_cache_present_before, "AC5: COLD child had cache before exec"
    assert draft_state == "cold" and not draft_cache_present, "AC5: draft materialized"
    assert buggy_state == "cold" and not buggy_cache_present, "AC8: buggy materialized"
    assert warm_reused == "1", "WARM child did not reuse the cache"
    assert cold_reused == "0", "COLD child unexpectedly reused"
    assert ignore_reused == "0", (
        "IGNORE control unexpectedly reused (prompt not isolated)"
    )
    assert ignore_cache_present_before, "IGNORE control missing materialized cache"
    for s in (warm_seconds, cold_seconds, ignore_seconds):
        assert s is not None and s > 0.0, "a measured wall-clock is null/non-positive"

    # ============================ EVIDENCE =================================== #
    result = {
        "host_note": (
            "canned scripts, no LLM/GPU — mechanism under test is helios materialize + "
            "the reuse-aware vs regenerate-always prompt embodiments"
        ),
        "prep_seconds_target": args.prep_seconds,
        "prep_iters": iters,
        "prep_array_bytes": _N * 8,
        "prep_array_mb": round(_N * 8 / 1e6, 2),
        "warm_seconds": warm_seconds,
        "cold_seconds": cold_seconds,
        "ignore_seconds": ignore_seconds,
        "materialize_note": (
            "warm_seconds is EXEC-only; the materialize (warm-start) overhead is a "
            "separate cost not folded into warm_seconds — reported so the number is honest"
        ),
        "speedup": speedup,
        "prompt_effect": prompt_effect,
        "speedup_benefit_threshold": _SPEEDUP_BENEFIT_THRESHOLD,
        "WARMSTART_VERDICT": verdict,
        "warm_reused": warm_reused == "1",
        "cold_reused": cold_reused == "1",
        "ignore_reused": ignore_reused == "1",
        "draft_state": draft_state,
        "buggy_state": buggy_state,
        "subtree_poison": poison["summary"],
        "torn_snapshot": torn["summary"],
    }
    _write_json(os.path.join(out_dir, "cold_vs_warm.json"), result)
    _write_md(os.path.join(out_dir, "cold_vs_warm.md"), result)
    _write_buggy_guard(
        os.path.join(out_dir, "buggy_guard.txt"),
        buggy_state,
        buggy_cache_present,
        buggy_dir_empty,
        draft_state,
        draft_cache_present,
    )
    _write_subtree_poison(os.path.join(out_dir, "subtree_poison.txt"), poison)
    _write_torn(os.path.join(out_dir, "torn_snapshot.txt"), torn)

    sys.stdout.write(
        "HARNESS_OK verdict=%s speedup=%.3f cold=%.3fs warm=%.3fs ignore=%.3fs "
        "prompt_effect=%.3f iters=%d\n"
        % (
            verdict,
            speedup,
            cold_seconds,
            warm_seconds,
            ignore_seconds,
            prompt_effect,
            iters,
        )
    )
    sys.stdout.write("out=%s store=%s binary=%s\n" % (out_dir, store_dir, binary))
    return 0


def _read_flag(work_dir):
    p = os.path.join(work_dir, "reused.flag")
    if not os.path.isfile(p):
        return "?"
    with open(p) as fh:
        return fh.read().strip()


def _run_subtree_poison(scratch, store, binary, store_dir, cfg_on, cfg_off, iters):
    """Wrong-but-valid parent cache; observe ON propagation vs OFF recomputation (AC9)."""
    root = os.path.join(scratch, "poison")
    os.makedirs(root)
    script = os.path.join(root, "node_code.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(_CANNED_SCRIPT)

    # Parent emits a WRONG-but-VALID cache: correct shape (N,), wrong values (all 42.0).
    p = _fresh_empty_dir(root, "P")
    wrong = np.full(_N, 42.0, dtype="float64")
    np.save(os.path.join(p, "preprocessed.npy"), wrong)
    parent_wrong_hash = _sha256(os.path.join(p, "preprocessed.npy"))
    sid_parent = store.snapshot(p)
    parent_node = SimpleNamespace(is_buggy=False, snapshot_id=sid_parent)

    # ---- ON: child reuses wrong cache, commit; grandchild reuses again -> propagates ----
    c_on = _fresh_empty_dir(root, "child_on")
    maybe_warm_start(cfg_on, parent_node, c_on)
    _run_script_local(script, c_on, iters, "reuse")
    child_on_hash = _sha256(os.path.join(c_on, "preprocessed.npy"))
    sid_child = store.snapshot(c_on)
    child_node = SimpleNamespace(is_buggy=False, snapshot_id=sid_child)

    g_on = _fresh_empty_dir(root, "grandchild_on")
    maybe_warm_start(cfg_on, child_node, g_on)
    _run_script_local(script, g_on, iters, "reuse")
    grandchild_on_hash = _sha256(os.path.join(g_on, "preprocessed.npy"))

    # ---- OFF: grandchild gets NO cache -> recomputes the correct bytes ----
    g_off = _fresh_empty_dir(root, "grandchild_off")
    maybe_warm_start(cfg_off, child_node, g_off)  # OFF -> no materialize
    _run_script_local(script, g_off, iters, "reuse")
    grandchild_off_hash = _sha256(os.path.join(g_off, "preprocessed.npy"))

    propagated_on = grandchild_on_hash == parent_wrong_hash
    recomputed_off = grandchild_off_hash != parent_wrong_hash
    return {
        "parent_wrong_hash": parent_wrong_hash,
        "child_on_hash": child_on_hash,
        "grandchild_on_hash": grandchild_on_hash,
        "grandchild_off_hash": grandchild_off_hash,
        "propagated_on": propagated_on,
        "recomputed_off": recomputed_off,
        "summary": {
            "propagated_on": propagated_on,
            "recomputed_off": recomputed_off,
        },
    }


def _run_torn_snapshot(scratch, store, cfg_on, iters):
    """Torn (truncated) .npy: bare np.load RAISES (real risk); reuse-aware regenerates (AC10)."""
    root = os.path.join(scratch, "torn")
    os.makedirs(root)
    script = os.path.join(root, "node_code.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(_CANNED_SCRIPT)

    # Build a real .npy then TRUNCATE to header-only bytes -> a torn snapshot artifact.
    p = _fresh_empty_dir(root, "P")
    cache = os.path.join(p, "preprocessed.npy")
    np.save(cache, np.zeros(1024, dtype="float64"))
    with open(cache, "r+b") as fh:
        fh.truncate(60)  # magic + partial header, no array payload
    sid_torn = store.snapshot(p)
    parent_node = SimpleNamespace(is_buggy=False, snapshot_id=sid_torn)

    child = _fresh_empty_dir(root, "child")
    maybe_warm_start(cfg_on, parent_node, child)

    # (1) a BARE np.load on the materialized torn file must RAISE (risk is real).
    bare_load_raised = False
    bare_load_tb = ""
    try:
        np.load(os.path.join(child, "preprocessed.npy"), allow_pickle=False)
    except Exception:
        bare_load_raised = True
        bare_load_tb = traceback.format_exc()

    # (2) the reuse-aware script over the SAME dir must produce a clean experiment_data.npy.
    _run_script_local(script, child, iters, "reuse")
    exp = os.path.join(child, "experiment_data.npy")
    clean_load_ok = False
    try:
        arr = np.load(exp, allow_pickle=False)
        clean_load_ok = arr.shape == (3,)
    except Exception:
        clean_load_ok = False

    return {
        "bare_load_raised": bare_load_raised,
        "bare_load_tb": bare_load_tb,
        "clean_load_ok": clean_load_ok,
        "summary": {
            "bare_load_raised": bare_load_raised,
            "clean_load_ok": clean_load_ok,
        },
    }


def _run_script_local(script, work_dir, iters, mode):
    env = os.environ.copy()
    env["HARNESS_N"] = str(_N)
    env["HARNESS_ITERS"] = str(iters)
    env["HARNESS_MODE"] = mode
    cp = subprocess.run(
        [sys.executable, script], cwd=work_dir, env=env, capture_output=True, text=True
    )
    if cp.returncode != 0:
        raise SystemExit("poison/torn script failed: %s" % cp.stderr)


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")


def _write_md(path, r):
    lines = []
    lines.append("# Warm-start cold-vs-warm measurement (Phase 7)\n")
    lines.append(
        "Deterministic replay harness. **No LLM, no GPU, no torch** on this host, so the "
        "node code is CANNED and the thing measured is the warm-start mechanism "
        "(`helios materialize`) plus the reuse-aware vs regenerate-always prompt "
        "embodiments — never a real research run.\n"
    )
    lines.append("## Measured wall-clock (`time.perf_counter`)\n")
    lines.append("| arm | prompt | cache before exec | seconds |")
    lines.append("|---|---|---|---|")
    lines.append(
        "| WARM | reuse-aware | present (materialized) | %.4f |" % r["warm_seconds"]
    )
    lines.append("| COLD | reuse-aware | absent | %.4f |" % r["cold_seconds"])
    lines.append(
        "| IGNORE (control) | regenerate-always | present (materialized) | %.4f |"
        % r["ignore_seconds"]
    )
    lines.append("")
    lines.append("## Derived ratios\n")
    lines.append("- `speedup = cold_seconds / warm_seconds` = **%.3f**" % r["speedup"])
    lines.append(
        "- `prompt_effect = ignore_seconds / warm_seconds` = **%.3f** "
        "(control: cache present but the regenerate-always prompt ignores it)"
        % r["prompt_effect"]
    )
    lines.append(
        "- prep: %d iters over a %.1f MB float64 array (target %.1fs/rebuild)"
        % (r["prep_iters"], r["prep_array_mb"], r["prep_seconds_target"])
    )
    lines.append("")
    lines.append("## Verdict\n")
    lines.append(
        "`speedup >= %.1f` ? -> **WARMSTART_VERDICT: %s**"
        % (r["speedup_benefit_threshold"], r["WARMSTART_VERDICT"])
    )
    lines.append("")
    lines.append("WARMSTART_VERDICT: %s\n" % r["WARMSTART_VERDICT"])
    lines.append("## Is the prompt change load-bearing?\n")
    if r["ignore_seconds"] >= 1.5 * r["warm_seconds"]:
        prompt_words = (
            "YES. With the cache **present on disk** but the prompt telling the model to "
            "regenerate everything (the IGNORE control), wall-clock stayed ~cold "
            "(`prompt_effect` ~= `speedup`): restoring files WITHOUT the reuse instruction "
            "bought nothing. The speedup is caused by the prompt change, not by the "
            "restore alone."
        )
    else:
        prompt_words = (
            "On this harness the IGNORE control did not run materially slower than WARM "
            "(`prompt_effect` ~= 1), so the restore-without-reuse-prompt effect was not "
            "isolated here. The control number is reported as measured, not asserted."
        )
    lines.append(prompt_words + "\n")
    lines.append("## Failure modes observed\n")
    lines.append(
        "- Subtree poison — ON propagated wrong-but-valid cache to grandchild: %s; "
        "OFF grandchild recomputed correct bytes: %s (see subtree_poison.txt)."
        % (r["subtree_poison"]["propagated_on"], r["subtree_poison"]["recomputed_off"])
    )
    lines.append(
        "- Torn snapshot — bare np.load raised: %s; reuse-aware regenerated a clean "
        "artifact: %s (see torn_snapshot.txt)."
        % (r["torn_snapshot"]["bare_load_raised"], r["torn_snapshot"]["clean_load_ok"])
    )
    lines.append("")
    lines.append("## Scope / honesty boundary\n")
    lines.append(
        "SYNTHETIC_HARNESS: no LLM/GPU on host — warm-start benefit on the REAL BFTS "
        "workload is UNMEASURED; mechanism demonstrated only\n"
    )
    lines.append(
        "REAL_RUN_REQUIRED_FOR_GENERALIZATION — the synthetic speedup above is NOT "
        "evidence that warm-start speeds up real research runs. It shows only that the "
        "mechanism (materialize a parent's cache into a fresh child dir + a reuse-aware "
        "prompt) eliminates a genuinely-cacheable prep step on a synthetic tree "
        "constructed to have one. Generalizing to the real workload requires a real run "
        "with a GPU/torch/LLM, where per-node dir size, cache reuse rate, and prep cost "
        "are all unknown on this host.\n"
    )
    lines.append(
        "Un-auto-detectable residual risk: a NON-buggy parent can still emit a "
        "wrong-but-valid cache (validation passes, values subtly wrong); warm-start then "
        "propagates it to the whole subtree. This is NOT guarded in code (see "
        "subtree_poison.txt) — it is mitigated only by (i) default-OFF and (ii) A/B "
        "accounting.\n"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _write_buggy_guard(
    path, buggy_state, buggy_cache, buggy_empty, draft_state, draft_cache
):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Buggy-parent + draft warm-start guard (AC8)\n\n")
        fh.write(
            "The debug branch deliberately re-enters buggy parents "
            "(parallel_agent `_debug`), and a buggy parent's snapshot may be torn or "
            "wrong. maybe_warm_start must therefore return 'cold' and materialize NOTHING "
            "for a buggy parent — else the buggy filesystem poisons the whole subtree.\n\n"
        )
        fh.write("buggy parent: maybe_warm_start -> %r\n" % buggy_state)
        fh.write("buggy child dir: preprocessed.npy present? %s\n" % buggy_cache)
        fh.write("buggy child dir empty? %s\n" % buggy_empty)
        fh.write("draft (parent=None): maybe_warm_start -> %r\n" % draft_state)
        fh.write("draft child dir: preprocessed.npy present? %s\n\n" % draft_cache)
        ok = (
            buggy_state == "cold"
            and not buggy_cache
            and buggy_empty
            and draft_state == "cold"
            and not draft_cache
        )
        fh.write("VERDICT: %s\n" % ("PASS" if ok else "FAIL"))


def _write_subtree_poison(path, poison):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Subtree poison: wrong-but-valid cache propagation (AC9)\n\n")
        fh.write(
            "A NON-buggy parent emits a cache with the CORRECT shape but WRONG values "
            "(all 42.0). Validation (shape/sanity) passes, so warm-start reuses it and "
            "propagates it down the branch. This wrong-but-valid case is "
            "UN-AUTO-DETECTABLE and is NOT guarded in code — it is gated only by "
            "default-OFF and A/B accounting.\n\n"
        )
        fh.write("parent wrong-but-valid hash: %s\n" % poison["parent_wrong_hash"])
        fh.write("child_on  preprocessed hash: %s\n" % poison["child_on_hash"])
        fh.write(
            "grandchild_on  preprocessed hash: %s\n" % poison["grandchild_on_hash"]
        )
        fh.write(
            "grandchild_off preprocessed hash: %s\n\n" % poison["grandchild_off_hash"]
        )
        fh.write(
            "ON  -> grandchild bytes == parent wrong bytes (poison propagated): %s\n"
            % poison["propagated_on"]
        )
        fh.write(
            "OFF -> grandchild bytes != parent wrong bytes (recomputed correct): %s\n\n"
            % poison["recomputed_off"]
        )
        fh.write(
            "VERDICT: %s\n"
            % (
                "PASS"
                if (poison["propagated_on"] and poison["recomputed_off"])
                else "FAIL"
            )
        )


def _write_torn(path, torn):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Torn snapshot survivability (AC10)\n\n")
        fh.write(
            "A timeout SIGKILL (interpreter.py) can leave a half-written .npy that Phase-5 "
            "then snapshots. Materializing that torn snapshot into a child and calling a "
            "BARE np.load on it RAISES (the risk is real). The reuse-aware script's "
            "validate-then-regenerate path recomputes it instead of crashing.\n\n"
        )
        fh.write("bare np.load on torn file raised: %s\n\n" % torn["bare_load_raised"])
        fh.write("---- bare np.load traceback ----\n")
        fh.write(torn["bare_load_tb"] or "(no traceback captured)\n")
        fh.write("\n---- reuse-aware regeneration ----\n")
        fh.write(
            "reuse-aware script produced a clean experiment_data.npy that np.loads: %s\n\n"
            % torn["clean_load_ok"]
        )
        fh.write(
            "VERDICT: %s\n"
            % (
                "PASS"
                if (torn["bare_load_raised"] and torn["clean_load_ok"])
                else "FAIL"
            )
        )


if __name__ == "__main__":
    raise SystemExit(main())
