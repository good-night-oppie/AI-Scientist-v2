"""Side-effects of item=68 + where the real divergence is. Correct alignment."""

import json
import sys
import glob
from collections import Counter, defaultdict

sys.path.insert(0, "/home/admin/gh/ready-player-one-ptcg/src")
from ready_player_one.ptcg import cards as db
from ready_player_one.ptcg import policy as P
from ready_player_one.ptcg.enums import *

RAW = "/home/admin/gh/ready-player-one-ptcg/runs/replay_mining/raw"
MINE = "/home/admin/gh/ready-player-one-ptcg/runs/replay_mining"
team_score = {e["team"]: e["score"] for e in json.load(open(f"{MINE}/manifest.json"))}
for f in ["inline_harvest_20260712.json", "inline_harvest_hop2_20260712.json"]:
    for k, v in json.load(open(f"{MINE}/{f}"))["decks"].items():
        team_score[v["team"]] = max(team_score.get(v["team"], 0), v["score"])
TN = {
    CARD_POKEMON: "POKE",
    CARD_SUPPORTER: "SUPPORTER",
    CARD_ITEM: "ITEM",
    CARD_STADIUM: "STADIUM",
    CARD_TOOL: "TOOL",
    CARD_BASIC_ENERGY: "BASIC_E",
}
OPTN = {
    7: "PLAY",
    8: "ATTACH",
    9: "EVOLVE",
    10: "ABILITY",
    12: "RETREAT",
    13: "ATTACK",
    14: "END",
}


def ctype(cid):
    c = db.card(cid)
    return TN.get(c["cardType"], "?") if c else "UNK"


def is_basic_poke(cid):
    c = db.card(cid)
    return bool(c and c["cardType"] == CARD_POKEMON and c.get("basic"))


conf = Counter()
agree = 0
n = 0
ib = (
    Counter()
)  # expert choice when BOTH a basic-pokemon play (bench<3) and an item play are legal
ib_null = 0.0
ib_n = 0
for fp in sorted(glob.glob(f"{RAW}/ep_*.json")):
    r = json.load(open(fp))
    steps = r["steps"]
    teams = r["info"]["TeamNames"]
    for i, st in enumerate(steps):
        if i + 1 >= len(steps):
            break
        for seat in (0, 1):
            rec = st[seat]
            if rec.get("status") != "ACTIVE":
                continue
            obs = rec.get("observation") or {}
            sel = obs.get("select")
            cur = obs.get("current")
            if not sel or cur is None or sel.get("type") != SEL_MAIN:
                continue
            if team_score.get(teams[seat], 0) < 1100:
                continue
            opts = sel.get("option") or []
            if not opts:
                continue
            me = cur.get("yourIndex", seat)
            act = steps[i + 1][seat].get("action")
            ai = (
                act[0]
                if isinstance(act, list) and act and 0 <= act[0] < len(opts)
                else None
            )
            if ai is None:
                continue
            sc = [
                P.score_option(j, o, SEL_MAIN, sel.get("context", 0), cur)
                for j, o in enumerate(opts)
            ]
            oi = max(range(len(opts)), key=lambda j: (sc[j], -j))
            e = OPTN.get(opts[ai].get("type"), "?")
            o = OPTN.get(opts[oi].get("type"), "?")
            conf[(e, o)] += 1
            n += 1
            agree += ai == oi
            # item vs bench-a-basic
            bench = len(cur["players"][me].get("bench", []))
            if bench >= 3:
                continue
            cids = [
                P._resolve_card_id(cur, me, AREA_HAND, x.get("index", 0))
                if x.get("type") == OPT_PLAY
                else None
                for x in opts
            ]
            nb = sum(1 for c in cids if c is not None and is_basic_poke(c))
            nit = sum(1 for c in cids if c is not None and ctype(c) == "ITEM")
            if nb and nit:
                ib_n += 1
                ib_null += nit / (nb + nit)
                ch = cids[ai] if opts[ai].get("type") == OPT_PLAY else None
                if ch is not None and is_basic_poke(ch):
                    ib["BENCH_A_BASIC"] += 1
                elif ch is not None and ctype(ch) == "ITEM":
                    ib["ITEM"] += 1
                else:
                    ib["other/non-play"] += 1

print(
    f"HI-RATED main states: {n}; exact option agreement expert-vs-our-policy: {agree} ({100 * agree / n:.1f}%)"
)
print("\nDIVERGENCE by expert option type (expert chose X -> we would choose Y):")
by_e = defaultdict(Counter)
for (e, o), c in conf.items():
    by_e[e][o] += c
for e in sorted(by_e, key=lambda x: -sum(by_e[x].values())):
    tot = sum(by_e[e].values())
    same = by_e[e][e]
    print(
        f"  expert {e:8s} n={tot:5d}  we-agree-on-type {100 * same / tot:5.1f}%   we instead: "
        + ", ".join(f"{k} {v}" for k, v in by_e[e].most_common(3) if k != e)
    )
print("\nOUR over-firing (we chose X; what the expert actually did there):")
by_o = defaultdict(Counter)
for (e, o), c in conf.items():
    by_o[o][e] += c
for o in sorted(by_o, key=lambda x: -sum(by_o[x].values())):
    tot = sum(by_o[o].values())
    print(
        f"  we {o:8s} n={tot:5d}  expert did: "
        + ", ".join(f"{k} {v}" for k, v in by_o[o].most_common(4))
    )

print(
    f"\nSIDE-EFFECT of item=68 (> basic-pokemon 66): states (bench<3) where BOTH a basic-pokemon play and an item play are legal: n={ib_n}"
)
for k, v in ib.most_common():
    print(f"   expert chose {k:16s} {v:5d}  ({100 * v / ib_n:.1f}%)")
print(
    f"   availability null for ITEM: {100 * ib_null / ib_n:.1f}%  -> experts bench basics FIRST far more than chance"
    if ib_n
    else ""
)
