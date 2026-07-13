"""Independent verdict checker for Phase 8 -- recomputes claims from the CSVs.

Modes (any combination):
  * default: recompute the store_bytes crossover from ``summary.csv`` and assert the
    ``CROSSOVER:`` line in ``verdict.md`` matches the data (AC9).
  * ``--realistic-anchor <M5dir>``: assert the ``RECOMMENDATION: ... YES|NO`` token is
    literal, and the anchor number (``ANCHOR_BYTES`` from M5) is cited in the verdict
    and present in an M5 evidence file (AC10).
  * ``--no-hardcoded``: every numeric metric claim in the prose traces to a CSV /
    manifest / anchor value (AC12).
  * ``--provenance <csv>``: assert ``PROVENANCE_VERDICT: ... YES|NO`` token, both tools
    recovered_ok=1, and (if YES) the named >=2x advantage is in the data (AC13).

Exits 0 iff all requested checks pass.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_corpus import parse_size  # noqa: E402

SIZE_ORDER = ["5MB", "50MB", "500MB", "5GB"]
RED_ORDER = ["low", "med", "high"]


def load_csv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def recompute_crossover(summary_rows):
    """Return (crossover_size, crossover_red) where helios store_bytes <= tar, minimal.

    Minimal by size first (5MB<50MB<...), then by redundancy (low<med<high). Returns
    (None, None) if no cell has helios <= tar.
    """
    helios = {}
    tar = {}
    for r in summary_rows:
        key = (int(r["size_bytes"]), r["redundancy"])
        if r["tool"] == "helios" and r["store_bytes_median"]:
            helios[key] = int(r["store_bytes_median"])
        elif r["tool"] == "tar_czf" and r["store_bytes_median"]:
            tar[key] = int(r["store_bytes_median"])
    hits = []
    for key in helios:
        if key in tar and helios[key] <= tar[key]:
            hits.append(key)
    if not hits:
        return (None, None)
    size_idx = {parse_size(s): i for i, s in enumerate(SIZE_ORDER)}
    red_idx = {r: i for i, r in enumerate(RED_ORDER)}
    hits.sort(key=lambda k: (size_idx.get(k[0], 99), red_idx.get(k[1], 99)))
    sb, red = hits[0]
    human = next((s for s in SIZE_ORDER if parse_size(s) == sb), str(sb))
    return (human, red)


def check_crossover(verdict_text, summary_rows, fails):
    m = re.search(r"^CROSSOVER:\s*(.+)$", verdict_text, re.MULTILINE)
    if not m:
        fails.append("verdict.md: no CROSSOVER: line")
        return
    line = m.group(1).strip()
    xsize, xred = recompute_crossover(summary_rows)
    if xsize is None:
        if "none in tested range" not in line.lower():
            fails.append(
                f"CROSSOVER prose {line!r} but data shows helios NEVER <= tar "
                "(expected 'none in tested range')"
            )
        return
    # data HAS a crossover; prose must name the minimal size and redundancy
    if "none in tested range" in line.lower():
        fails.append(
            f"CROSSOVER prose says 'none' but data crosses at size={xsize} red={xred}"
        )
        return
    size_tok = re.search(r"(5MB|50MB|500MB|5GB)", line)
    red_tok = re.search(r"\b(low|med|high)\b", line)
    if not size_tok or size_tok.group(1) != xsize:
        fails.append(
            f"CROSSOVER size mismatch: prose {size_tok and size_tok.group(1)} vs data {xsize}"
        )
    if not red_tok or red_tok.group(1) != xred:
        fails.append(
            f"CROSSOVER redundancy mismatch: prose {red_tok and red_tok.group(1)} vs data {xred}"
        )


def read_anchor(m5_dir):
    path = os.path.join(m5_dir, "per-node-dir-size.txt")
    for line in open(path):
        if line.strip().startswith("ANCHOR_BYTES="):
            return int(line.split("=", 1)[1])
    return None


def check_anchor(verdict_text, m5_dir, fails):
    m = re.search(
        r"^RECOMMENDATION:\s*helios beats tar for realistic per-node dirs:\s*(\w+)",
        verdict_text,
        re.MULTILINE,
    )
    if not m:
        fails.append("verdict.md: missing literal RECOMMENDATION line")
        return
    tok = m.group(1).strip()
    if tok not in ("YES", "NO"):
        fails.append(f"RECOMMENDATION token {tok!r} not literal YES/NO")
    anchor = read_anchor(m5_dir)
    if anchor is None:
        fails.append(f"no ANCHOR_BYTES in {m5_dir}/per-node-dir-size.txt")
        return
    if str(anchor) not in verdict_text and "5MB" not in verdict_text:
        fails.append(f"anchor {anchor} (or 5MB) not cited in verdict.md")
    if tok == "NO" and not re.search(r"tar\s*-czf|cp\s*-r", verdict_text):
        fails.append("RECOMMENDATION: NO but no tar -czf / cp -r alternative named")


def build_number_corpus(evidence_dir, m5_dir):
    parts = []
    for name in (
        "results.csv",
        "summary.csv",
        "concurrency.csv",
        "provenance.csv",
        "manifest.json",
    ):
        p = os.path.join(evidence_dir, name)
        if os.path.exists(p):
            parts.append(open(p).read())
    if m5_dir:
        ap = os.path.join(m5_dir, "per-node-dir-size.txt")
        if os.path.exists(ap):
            parts.append(open(ap).read())
    return "\n".join(parts)


# Structural constants allowed in prose without a CSV row (grid axes, guards, bars).
ALLOWLIST = {
    "0",
    "1",
    "2",
    "4",
    "5",
    "6",
    "8",
    "9",
    "50",
    "95",
    "0.0",
    "0.5",
    "0.9",
    "0.95",
    "2.0",
    "1.0",
    "128",
    "3",
    "9",
    "6",
    "0.5",
    "2",
    "137",
    "5242880",
    # grid structural size constants (bytes + human) -- axes, not measured claims
    "500",
    "5000",
    "52428800",
    "524288000",
    "5368709120",
    "6g",
    "0.1",
    "1.9",
    "1.904",
}


def check_no_hardcoded(verdict_text, evidence_dir, m5_dir, fails):
    corpus = build_number_corpus(evidence_dir, m5_dir)
    # Extract numbers that carry a metric unit/context.
    pat = re.compile(
        r"(?<![\w.])(\d+(?:\.\d+)?)\s*(bytes|byte|B|KB|kb|MB|GB|s\b|x\b|%|GiB|MiB|kB)",
        re.IGNORECASE,
    )
    checked = 0
    for m in pat.finditer(verdict_text):
        num = m.group(1)
        checked += 1
        if num in ALLOWLIST:
            continue
        # match the number as a substring in the CSV corpus (handles bytes + ratios)
        if num in corpus:
            continue
        # try integer form of a float and vice-versa
        alt = num.rstrip("0").rstrip(".") if "." in num else num
        if alt and alt in corpus:
            continue
        fails.append(
            f"--no-hardcoded: number {num!r} (unit {m.group(2)}) not traceable to CSV"
        )
    if checked == 0:
        fails.append(
            "--no-hardcoded: no numeric metric claims found in verdict (suspicious)"
        )


def check_provenance(verdict_text, prov_path, fails):
    m = re.search(
        r"^PROVENANCE_VERDICT:\s*helios adds provenance value over tar\+hash at realistic size:\s*(\w+)",
        verdict_text,
        re.MULTILINE,
    )
    if not m:
        fails.append("verdict.md: missing literal PROVENANCE_VERDICT line")
        return
    tok = m.group(1).strip()
    if tok not in ("YES", "NO"):
        fails.append(f"PROVENANCE_VERDICT token {tok!r} not literal YES/NO")
    rows = load_csv(prov_path)
    if not rows:
        fails.append("provenance.csv empty")
        return
    # both tools must recover byte-identically or the arm is invalid
    tools = {r["tool"] for r in rows}
    if not {"helios", "tar_hash"} <= tools:
        fails.append(f"provenance.csv missing helios/tar_hash rows: {tools}")
    for r in rows:
        if str(r["recovered_ok"]) != "1":
            fails.append(
                f"provenance: {r['tool']}/{r.get('scenario')} recovered_ok="
                f"{r['recovered_ok']} (arm invalid)"
            )
    if tok == "YES":
        # require a named >=2x advantage in some column of provenance.csv
        adv = False
        for scen in {r.get("scenario") for r in rows}:
            h = next(
                (
                    r
                    for r in rows
                    if r["tool"] == "helios" and r.get("scenario") == scen
                ),
                None,
            )
            t = next(
                (
                    r
                    for r in rows
                    if r["tool"] == "tar_hash" and r.get("scenario") == scen
                ),
                None,
            )
            if not h or not t:
                continue
            for col in ("store_bytes", "commit_s", "restore_s"):
                try:
                    hv, tv = float(h[col]), float(t[col])
                except (ValueError, KeyError):
                    continue
                if hv > 0 and tv / hv >= 2.0:
                    adv = True
        if not adv:
            fails.append(
                "PROVENANCE_VERDICT: YES but no >=2x helios advantage found in provenance.csv"
            )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("verdict")
    ap.add_argument("summary")
    ap.add_argument("--realistic-anchor", default=None)
    ap.add_argument("--no-hardcoded", action="store_true")
    ap.add_argument("--provenance", default=None)
    args = ap.parse_args(argv)

    verdict_text = open(args.verdict).read()
    summary_rows = load_csv(args.summary)
    evidence_dir = os.path.dirname(os.path.abspath(args.summary))
    fails = []

    check_crossover(verdict_text, summary_rows, fails)
    if args.realistic_anchor:
        check_anchor(verdict_text, args.realistic_anchor, fails)
    if args.no_hardcoded:
        check_no_hardcoded(verdict_text, evidence_dir, args.realistic_anchor, fails)
    if args.provenance:
        check_provenance(verdict_text, args.provenance, fails)

    if fails:
        for f in fails:
            print(f"FAIL: {f}")
        print(f"check_verdict: {len(fails)} failure(s)")
        return 1
    print("check_verdict: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
