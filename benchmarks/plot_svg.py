"""Hand-rolled SVG crossover plot -- pure stdlib (the usual plotting lib is absent).

Two stacked panels, both log-x on per-node size:
  * top:    helios_store_bytes / tar_store_bytes   (the dedup claim)
  * bottom: helios_commit_s   / tar_commit_s        (the latency cost)
One polyline per redundancy level, a horizontal y=1.0 break-even line, and a
vertical dashed marker at the realistic per-node anchor size (from Phase 5 / M5).
Output is valid XML (parseable by ``xml.dom.minidom``); pure stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_corpus import parse_size  # noqa: E402

RED_COLORS = {"low": "#d62728", "med": "#ff7f0e", "high": "#2ca02c"}


def load_summary(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def collect(rows, ratio_col):
    """Return {redundancy: [(size_bytes, ratio), ...]} sorted by size."""
    out = {}
    for r in rows:
        if r["tool"] != "helios":
            continue
        val = r.get(ratio_col, "")
        if val in ("", None):
            continue
        out.setdefault(r["redundancy"], []).append((int(r["size_bytes"]), float(val)))
    for k in out:
        out[k].sort()
    return out


def _anchor_bytes(explicit):
    if explicit:
        return parse_size(explicit) if not str(explicit).isdigit() else int(explicit)
    for cand in (
        os.path.join(
            "..", "..", "..", ".supergoal", "evidence", "M5", "per-node-dir-size.txt"
        ),
        os.path.join(".supergoal", "evidence", "M5", "per-node-dir-size.txt"),
    ):
        if os.path.exists(cand):
            for line in open(cand):
                if line.strip().startswith("ANCHOR_BYTES="):
                    return int(line.split("=", 1)[1])
    return 5242880  # 5MB fallback


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def panel(series, anchor, x0, y0, w, h, title, sizes_all):
    """Render one panel; return SVG fragment string."""
    frag = []
    lo = math.log10(min(sizes_all))
    hi = math.log10(max(sizes_all))
    span = hi - lo or 1.0
    # ratio y-range
    all_r = [v for s in series.values() for (_, v) in s] + [1.0]
    rmax = max(all_r) * 1.15
    rmin = 0.0

    def sx(sb):
        return x0 + (math.log10(sb) - lo) / span * w

    def sy(r):
        return y0 + h - (r - rmin) / (rmax - rmin or 1.0) * h

    # frame
    frag.append(
        f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="none" '
        f'stroke="#888" stroke-width="1"/>'
    )
    frag.append(
        f'<text x="{x0 + w / 2}" y="{y0 - 8}" font-size="14" text-anchor="middle" '
        f'font-family="sans-serif">{esc(title)}</text>'
    )
    # break-even y=1.0
    yb = sy(1.0)
    frag.append(
        f'<line x1="{x0}" y1="{yb:.1f}" x2="{x0 + w}" y2="{yb:.1f}" '
        f'stroke="#333" stroke-width="1" stroke-dasharray="6 3"/>'
    )
    frag.append(
        f'<text x="{x0 + w - 4}" y="{yb - 4:.1f}" font-size="11" text-anchor="end" '
        f'font-family="sans-serif" fill="#333">break-even (y=1.0)</text>'
    )
    # vertical anchor marker
    if min(sizes_all) <= anchor <= max(sizes_all):
        xa = sx(anchor)
    else:
        xa = sx(min(sizes_all)) if anchor < min(sizes_all) else sx(max(sizes_all))
    frag.append(
        f'<line x1="{xa:.1f}" y1="{y0}" x2="{xa:.1f}" y2="{y0 + h}" '
        f'stroke="#1f77b4" stroke-width="1.5" stroke-dasharray="3 3"/>'
    )
    frag.append(
        f'<text x="{xa + 4:.1f}" y="{y0 + 14}" font-size="11" '
        f'font-family="sans-serif" fill="#1f77b4">anchor {anchor}B (5MB)</text>'
    )
    # x ticks
    for sb in sizes_all:
        x = sx(sb)
        frag.append(
            f'<line x1="{x:.1f}" y1="{y0 + h}" x2="{x:.1f}" y2="{y0 + h + 4}" '
            f'stroke="#888"/>'
        )
        human = next(
            (s for s in ("5MB", "50MB", "500MB", "5GB") if parse_size(s) == sb), str(sb)
        )
        frag.append(
            f'<text x="{x:.1f}" y="{y0 + h + 16}" font-size="11" text-anchor="middle" '
            f'font-family="sans-serif">{esc(human)}</text>'
        )
    # y ticks
    for frac in (0.0, 0.5, 1.0):
        rv = rmin + frac * (rmax - rmin)
        y = sy(rv)
        frag.append(
            f'<line x1="{x0 - 4}" y1="{y:.1f}" x2="{x0}" y2="{y:.1f}" stroke="#888"/>'
        )
        frag.append(
            f'<text x="{x0 - 6}" y="{y + 3:.1f}" font-size="10" text-anchor="end" '
            f'font-family="sans-serif">{rv:.2f}</text>'
        )
    # series lines
    for red, pts in sorted(series.items()):
        color = RED_COLORS.get(red, "#555")
        coords = " ".join(f"{sx(sb):.1f},{sy(v):.1f}" for sb, v in pts)
        if coords:
            frag.append(
                f'<polyline points="{coords}" fill="none" stroke="{color}" '
                f'stroke-width="2"/>'
            )
        for sb, v in pts:
            frag.append(
                f'<circle cx="{sx(sb):.1f}" cy="{sy(v):.1f}" r="3" fill="{color}"/>'
            )
    return "\n".join(frag)


def build_svg(summary_rows, anchor):
    store = collect(summary_rows, "helios_over_tar_store")
    commit = collect(summary_rows, "helios_over_tar_commit")
    sizes_all = sorted(
        {
            int(r["size_bytes"])
            for r in summary_rows
            if r["tool"] == "helios" and r.get("helios_over_tar_store")
        }
    )
    if not sizes_all:
        sizes_all = sorted({int(r["size_bytes"]) for r in summary_rows})
    W, H = 720, 640
    x0, w = 90, 560
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="white"/>',
        '<text x="360" y="24" font-size="17" text-anchor="middle" '
        'font-family="sans-serif" font-weight="bold">helios / tar crossover '
        "(lower is better for helios; below 1.0 = helios wins)</text>",
    ]
    parts.append(
        panel(
            store, anchor, x0, 60, w, 210, "store_bytes ratio  helios / tar", sizes_all
        )
    )
    parts.append(
        panel(
            commit, anchor, x0, 360, w, 210, "commit_s ratio  helios / tar", sizes_all
        )
    )
    # legend
    ly = 600
    lx = x0
    for red in ("low", "med", "high"):
        parts.append(
            f'<rect x="{lx}" y="{ly - 10}" width="14" height="10" '
            f'fill="{RED_COLORS[red]}"/>'
        )
        parts.append(
            f'<text x="{lx + 18}" y="{ly}" font-size="12" '
            f'font-family="sans-serif">redundancy={red}</text>'
        )
        lx += 150
    parts.append("</svg>")
    return "\n".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--anchor", default=None)
    args = ap.parse_args(argv)
    rows = load_summary(args.inp)
    anchor = _anchor_bytes(args.anchor)
    svg = build_svg(rows, anchor)
    with open(args.out, "w") as fh:
        fh.write(svg)
    # self-validate: parse as XML
    import xml.dom.minidom

    xml.dom.minidom.parseString(svg)
    print(f"wrote {args.out} (valid XML, anchor={anchor})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
