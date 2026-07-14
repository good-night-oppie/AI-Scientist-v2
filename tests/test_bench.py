"""Phase 8 benchmark unit tests (run under .venv-test/bin/python).

Covers: (a) gen_corpus determinism, (b) results/summary schema round-trip,
(c) plot_svg parses as XML and imports no matplotlib, (d) check_grid/check_verdict
FAIL on deliberately corrupted fixtures (proving the checkers actually check).
"""

from __future__ import annotations

import csv
import os
import sys
import xml.dom.minidom

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
BENCH = os.path.join(REPO, "benchmarks")
sys.path.insert(0, BENCH)

import bench  # noqa: E402
import check_grid  # noqa: E402
import check_verdict  # noqa: E402
import gen_corpus  # noqa: E402
import plot_svg  # noqa: E402


def test_corpus_determinism(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    gen_corpus.gen_corpus(5 * 1024 * 1024, "med", 6, 1234, str(a))
    gen_corpus.gen_corpus(5 * 1024 * 1024, "med", 6, 1234, str(b))
    assert gen_corpus.sha256_tree(str(a)) == gen_corpus.sha256_tree(str(b))


def test_corpus_seed_changes_unique_not_shared(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    gen_corpus.gen_corpus(2 * 1024 * 1024, "high", 4, 1, str(a))
    gen_corpus.gen_corpus(2 * 1024 * 1024, "high", 4, 2, str(b))
    # different seed -> different trees
    assert gen_corpus.sha256_tree(str(a)) != gen_corpus.sha256_tree(str(b))


def test_measured_redundancy_matches_target(tmp_path):
    for red, target in (("low", 0.0), ("med", 0.5), ("high", 0.95)):
        out = tmp_path / red
        gen_corpus.gen_corpus(4 * 1024 * 1024, red, 6, 7, str(out))
        meas = gen_corpus.measured_redundancy(str(out), 6)
        assert abs(meas - target) <= 0.02, f"{red}: measured {meas} vs {target}"


def test_parse_size():
    assert gen_corpus.parse_size("5MB") == 5 * 1024 * 1024
    assert gen_corpus.parse_size("50MB") == 50 * 1024 * 1024
    assert gen_corpus.parse_size("5GB") == 5 * 1024 * 1024 * 1024


def _write_good_results(path):
    fields = bench.RESULTS_FIELDS
    rows = []
    sizes = {
        "5MB": 5 * 1024 * 1024,
        "50MB": 50 * 1024 * 1024,
        "500MB": 500 * 1024 * 1024,
        "5GB": 5 * 1024 * 1024 * 1024,
    }
    for tool in ["helios", "cp_r", "tar_czf"]:
        for sname, sb in sizes.items():
            for red in ["low", "med", "high"]:
                for rep in range(6):
                    rows.append(
                        {
                            "tool": tool,
                            "size_bytes": sb,
                            "redundancy": red,
                            "n_nodes": 6,
                            "rep": rep,
                            "phase_commit_s": 1.0,
                            "phase_restore_s": 0.5,
                            "store_bytes": sb,
                            "peak_rss_kb": 1000,
                            "round_trip_ok": 1,
                            "oomed": 0,
                            "skipped_reason": "",
                        }
                    )
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return rows


def _write_summary_from(rows, path):
    completed = [r for r in rows if not r["skipped_reason"] and int(r["rep"]) >= 1]
    summ = bench.add_helios_tar_ratios(bench.summarize(completed))
    fields = [
        "tool",
        "size_bytes",
        "redundancy",
        "n_reps",
        "commit_s_median",
        "commit_s_p90",
        "restore_s_median",
        "restore_s_p90",
        "store_bytes_median",
        "peak_rss_kb_median",
        "round_trip_ok",
        "oomed",
        "helios_over_tar_store",
        "helios_over_tar_commit",
    ]
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for s in summ:
            w.writerow({k: s.get(k, "") for k in fields})


def test_results_summary_schema_roundtrip(tmp_path):
    rp = tmp_path / "results.csv"
    rows = _write_good_results(str(rp))
    back = list(csv.DictReader(open(rp)))
    assert [set(r) for r in back][0] == set(bench.RESULTS_FIELDS)
    sp = tmp_path / "summary.csv"
    _write_summary_from(rows, str(sp))
    # a good grid + summary + dedup must pass check_grid
    dg = tmp_path / "dedup_granularity.txt"
    dg.write_text("FILESIZE_BYTES=1000\nDELTA_BYTES=1000\nGRANULARITY=whole-file\n")
    assert check_grid.main([str(rp)]) == 0


def test_check_grid_fails_on_missing_cell(tmp_path):
    rp = tmp_path / "results.csv"
    rows = _write_good_results(str(rp))
    # drop all rows for one cell
    rows = [
        r
        for r in rows
        if not (
            r["tool"] == "helios"
            and r["redundancy"] == "high"
            and r["size_bytes"] == 5 * 1024 * 1024
        )
    ]
    with open(rp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=bench.RESULTS_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    _write_summary_from(rows, str(tmp_path / "summary.csv"))
    (tmp_path / "dedup_granularity.txt").write_text(
        "FILESIZE_BYTES=1000\nDELTA_BYTES=1000\nGRANULARITY=whole-file\n"
    )
    assert check_grid.main([str(rp)]) == 1


def test_check_grid_fails_on_roundtrip_zero(tmp_path):
    rp = tmp_path / "results.csv"
    rows = _write_good_results(str(rp))
    rows[0]["round_trip_ok"] = 0  # a corrupted (disqualified) cell
    with open(rp, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=bench.RESULTS_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    _write_summary_from(rows, str(tmp_path / "summary.csv"))
    (tmp_path / "dedup_granularity.txt").write_text(
        "FILESIZE_BYTES=1000\nDELTA_BYTES=1000\nGRANULARITY=whole-file\n"
    )
    assert check_grid.main([str(rp)]) == 1


def test_check_grid_dedup_numeric_guard(tmp_path):
    rp = tmp_path / "results.csv"
    rows = _write_good_results(str(rp))
    _write_summary_from(rows, str(tmp_path / "summary.csv"))
    # GRANULARITY=whole-file but delta ~ 0 => must FAIL
    (tmp_path / "dedup_granularity.txt").write_text(
        "FILESIZE_BYTES=1000\nDELTA_BYTES=10\nGRANULARITY=whole-file\n"
    )
    assert check_grid.main([str(rp)]) == 1


def test_concurrency_checker(tmp_path):
    cc = tmp_path / "concurrency.csv"
    fields = ["config", "K", "wall_s", "commits_ok", "commits_failed", "throughput_cps"]
    good = []
    for K in [1, 2, 4, 8]:
        good.append(
            {
                "config": "helios+flock",
                "K": K,
                "wall_s": 1,
                "commits_ok": K,
                "commits_failed": 0,
                "throughput_cps": 1,
            }
        )
        good.append(
            {
                "config": "helios-flock",
                "K": K,
                "wall_s": 1,
                "commits_ok": K if K == 1 else K - 1,
                "commits_failed": 0 if K == 1 else 1,
                "throughput_cps": 1,
            }
        )
        good.append(
            {
                "config": "tar",
                "K": K,
                "wall_s": 1,
                "commits_ok": K,
                "commits_failed": 0,
                "throughput_cps": 1,
            }
        )
    with open(cc, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in good:
            w.writerow(r)
    assert check_grid.main([str(cc), "--concurrency"]) == 0
    # break the load-bearing predicate: helios-flock never fails
    for r in good:
        if r["config"] == "helios-flock":
            r["commits_failed"] = 0
            r["commits_ok"] = r["K"]
    with open(cc, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in good:
            w.writerow(r)
    assert check_grid.main([str(cc), "--concurrency"]) == 1


def test_plot_svg_parses_and_no_matplotlib(tmp_path):
    # plot_svg.py must not import matplotlib
    src = open(os.path.join(BENCH, "plot_svg.py")).read()
    assert "matplotlib" not in src
    rp = tmp_path / "results.csv"
    rows = _write_good_results(str(rp))
    sp = tmp_path / "summary.csv"
    _write_summary_from(rows, str(sp))
    svg = tmp_path / "crossover.svg"
    assert (
        plot_svg.main(["--in", str(sp), "--out", str(svg), "--anchor", "5242880"]) == 0
    )
    xml.dom.minidom.parse(str(svg))  # raises if invalid


def test_check_verdict_crossover_mismatch(tmp_path):
    rp = tmp_path / "results.csv"
    rows = _write_good_results(str(rp))
    # make helios store 2x tar everywhere => data crossover = none
    for r in rows:
        if r["tool"] == "helios":
            r["store_bytes"] = int(r["store_bytes"]) * 2
    sp = tmp_path / "summary.csv"
    _write_summary_from(rows, str(sp))
    # prose falsely claims a crossover -> must FAIL
    vd = tmp_path / "verdict.md"
    vd.write_text(
        "CROSSOVER: helios <= tar on store_bytes at size >= 5MB for redundancy >= low\n"
    )
    assert check_verdict.main([str(vd), str(sp)]) == 1
    # honest prose -> must PASS
    vd.write_text("CROSSOVER: none in tested range\n")
    assert check_verdict.main([str(vd), str(sp)]) == 0


def test_check_verdict_provenance_token(tmp_path):
    sp = tmp_path / "summary.csv"
    rows = _write_good_results(str(tmp_path / "results.csv"))
    for (
        r
    ) in rows:  # helios stores 2x tar => no crossover => "none in tested range" honest
        if r["tool"] == "helios":
            r["store_bytes"] = int(r["store_bytes"]) * 2
    _write_summary_from(rows, str(sp))
    prov = tmp_path / "provenance.csv"
    prov.write_text(
        "tool,scenario,recovered_ok,store_bytes,commit_s,restore_s\n"
        "helios,single_node,1,100,1.0,1.0\n"
        "tar_hash,single_node,1,100,1.0,1.0\n"
    )
    vd = tmp_path / "verdict.md"
    # NO with both recovered_ok=1 -> PASS
    vd.write_text(
        "CROSSOVER: none in tested range\n"
        "PROVENANCE_VERDICT: helios adds provenance value over tar+hash at "
        "realistic size: NO\n"
    )
    assert check_verdict.main([str(vd), str(sp), "--provenance", str(prov)]) == 0
    # YES without a >=2x advantage -> FAIL
    vd.write_text(
        "CROSSOVER: none in tested range\n"
        "PROVENANCE_VERDICT: helios adds provenance value over tar+hash at "
        "realistic size: YES\n"
    )
    assert check_verdict.main([str(vd), str(sp), "--provenance", str(prov)]) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
