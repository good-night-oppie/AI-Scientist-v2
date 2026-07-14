#!/usr/bin/env python3
"""Honesty-gate verifier for the Phase-7 warm-start evidence (AC6, AC7, AC7b).

Asserts that ``cold_vs_warm.json`` and ``cold_vs_warm.md`` are HONEST and COMPLETE — it
does **NOT** assert any speedup inequality. Specifically:

  AC6  warm_seconds / cold_seconds / ignore_seconds are present, non-null, > 0 (real
       ``time.perf_counter`` values); ``speedup == cold/warm`` (within tolerance); and the
       ``WARMSTART_VERDICT`` token equals ``BENEFIT`` iff ``speedup >= 1.5`` else
       ``NO_BENEFIT`` — i.e. the token MATCHES ITS OWN ARITHMETIC. A ``NO_BENEFIT`` verdict
       PASSES: the phase measures the mechanism, it does not manufacture a win.
  AC7  ``ignore_seconds`` (the control arm) and ``prompt_effect == ignore/warm`` are
       present and non-null (the prompt-change control number is reported, not asserted).
  AC7b ``cold_vs_warm.md`` contains BOTH anti-over-claim markers verbatim.

Usage: check_warm_start.py <cold_vs_warm.json> <cold_vs_warm.md>
Exit 0 iff every check passes; SystemExit(msg) otherwise.
"""

from __future__ import annotations

import json
import sys

_BENEFIT_THRESHOLD = 1.5
_MARKER_SYNTH = (
    "SYNTHETIC_HARNESS: no LLM/GPU on host — warm-start benefit on the REAL BFTS "
    "workload is UNMEASURED; mechanism demonstrated only"
)
_MARKER_REAL = "REAL_RUN_REQUIRED_FOR_GENERALIZATION"


def _fail(msg):
    raise SystemExit("CHECK_WARM_START FAIL: " + msg)


def _is_pos_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x > 0.0


def main(argv):
    if len(argv) < 3:
        _fail("usage: check_warm_start.py <cold_vs_warm.json> <cold_vs_warm.md>")
    json_path, md_path = argv[1], argv[2]

    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    with open(md_path, "r", encoding="utf-8") as fh:
        md = fh.read()

    # --- AC6: three real, non-null, positive wall-clock numbers -------------------
    for key in ("warm_seconds", "cold_seconds", "ignore_seconds"):
        if key not in data:
            _fail("missing key %r" % key)
        if data[key] is None:
            _fail("%s is null" % key)
        if not _is_pos_number(data[key]):
            _fail("%s is not a positive number: %r" % (key, data[key]))

    warm = float(data["warm_seconds"])
    cold = float(data["cold_seconds"])
    ignore = float(data["ignore_seconds"])

    # --- AC6: speedup present and equals cold/warm --------------------------------
    if "speedup" not in data or data["speedup"] is None:
        _fail("missing/null speedup")
    speedup = float(data["speedup"])
    expected_speedup = cold / warm
    if abs(speedup - expected_speedup) > 1e-6 * max(1.0, abs(expected_speedup)):
        _fail("speedup %r != cold/warm %r" % (speedup, expected_speedup))

    # --- AC6: verdict token MATCHES its own arithmetic (NO inequality asserted) ----
    if "WARMSTART_VERDICT" not in data:
        _fail("missing WARMSTART_VERDICT in json")
    verdict = data["WARMSTART_VERDICT"]
    expected_verdict = "BENEFIT" if speedup >= _BENEFIT_THRESHOLD else "NO_BENEFIT"
    if verdict != expected_verdict:
        _fail(
            "WARMSTART_VERDICT %r contradicts its arithmetic (speedup=%.4f -> %r)"
            % (verdict, speedup, expected_verdict)
        )
    # The md must also carry the literal token line, consistent with the json.
    if ("WARMSTART_VERDICT: %s" % verdict) not in md:
        _fail("md missing literal 'WARMSTART_VERDICT: %s' line" % verdict)

    # --- AC7: control arm number + prompt_effect present and non-null --------------
    if "prompt_effect" not in data or data["prompt_effect"] is None:
        _fail("missing/null prompt_effect (control ratio)")
    prompt_effect = float(data["prompt_effect"])
    expected_pe = ignore / warm
    if abs(prompt_effect - expected_pe) > 1e-6 * max(1.0, abs(expected_pe)):
        _fail("prompt_effect %r != ignore/warm %r" % (prompt_effect, expected_pe))

    # --- AC7b: anti-over-claim markers present verbatim ----------------------------
    if _MARKER_SYNTH not in md:
        _fail("cold_vs_warm.md missing SYNTHETIC_HARNESS marker (verbatim)")
    if _MARKER_REAL not in md:
        _fail("cold_vs_warm.md missing REAL_RUN_REQUIRED_FOR_GENERALIZATION marker")

    sys.stdout.write(
        "CHECK_WARM_START OK: warm=%.4fs cold=%.4fs ignore=%.4fs speedup=%.3f "
        "prompt_effect=%.3f verdict=%s (verdict matches arithmetic; NO inequality "
        "asserted; both scope markers present)\n"
        % (warm, cold, ignore, speedup, prompt_effect, verdict)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
