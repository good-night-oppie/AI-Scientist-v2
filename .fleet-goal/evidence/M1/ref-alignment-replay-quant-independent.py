#!/usr/bin/env python3
"""REPLAY-QUANT: engine-free recomputation of divergence-spec behavioral claims
from the 106 raw Kaggle replays (runs/replay_mining/raw/ep_*.json).

Alignment convention (validated): steps[t+1][seat].action answers
steps[t][seat].observation.select.  Card classes are inferred from replay
dynamics only (no engine, no card DB):
  pokemon  = id seen in an in-play stack entry (has maxHp) or preEvolution
  energy   = id seen inside a stack's energyCards list
  tool     = id seen inside a stack's tools list
  stadium  = id seen as current.stadium
  supporter= PLAY-chosen id whose play flips current.supporterPlayed False->True
  item     = PLAY-chosen id that never flips supporterPlayed and is in no other class
"""

import json
import glob
import os
import statistics
import collections

RAW = "/home/admin/gh/ready-player-one-ptcg/runs/replay_mining/raw"
RM = "/home/admin/gh/ready-player-one-ptcg/runs/replay_mining"
OUT = os.path.dirname(os.path.abspath(__file__))

# enum labels (integer codes from the cabt engine spec, mirrored in
# ready_player_one/ptcg/enums.py -- label mapping only, no engine code)
OPT_PLAY, OPT_ATTACH, OPT_EVOLVE, OPT_ABILITY, OPT_RETREAT, OPT_ATTACK, OPT_END = (
    7,
    8,
    9,
    10,
    12,
    13,
    14,
)
AREA_ACTIVE, AREA_BENCH = 4, 5
CTX_MAIN, CTX_TO_DECK = 0, 9

# ---------- rating map ----------
team_score = {}
for hf in ("inline_harvest_20260712.json", "inline_harvest_hop2_20260712.json"):
    d = json.load(open(os.path.join(RM, hf)))
    for k, v in d["decks"].items():
        team_score[v["team"]] = max(team_score.get(v["team"], 0), v["score"])

files = sorted(glob.glob(RAW + "/ep_*.json"))

# ---------- pass 1: card classification from dynamics + names ----------
id_name = {}
pokemon_ids, energy_ids, tool_ids, stadium_ids = set(), set(), set(), set()
supporter_votes = collections.Counter()  # id -> flips seen
play_votes = collections.Counter()  # id -> times seen as chosen PLAY


def walk_names(o):
    if isinstance(o, dict):
        if "id" in o and "name" in o:
            id_name.setdefault(o["id"], o["name"])
        for v in o.values():
            walk_names(v)
    elif isinstance(o, list):
        for v in o:
            walk_names(v)


def scan_stacks(cur):
    if not cur:
        return
    st = cur.get("stadium")
    if isinstance(st, dict) and "id" in st:
        stadium_ids.add(st["id"])
    elif isinstance(st, int) and st > 0:
        stadium_ids.add(st)
    elif isinstance(st, list):
        for s in st:
            if isinstance(s, dict) and "id" in s:
                stadium_ids.add(s["id"])
    for pl in cur.get("players", []):
        for area in ("active", "bench"):
            for mon in pl.get(area, []):
                if isinstance(mon, dict) and "maxHp" in mon:
                    pokemon_ids.add(mon["id"])
                    for e in mon.get("energyCards", []):
                        energy_ids.add(e["id"] if isinstance(e, dict) else e)
                    for tl in mon.get("tools", []):
                        tool_ids.add(tl["id"] if isinstance(tl, dict) else tl)
                    for pe in mon.get("preEvolution", []):
                        if isinstance(pe, dict) and "id" in pe:
                            pokemon_ids.add(pe["id"])


episodes = []  # per-episode meta
decisions = []  # per-decision records (dicts)
retreat_events = []  # (ep, seat, t, serial, e_before, e_after_or_None)

for f in files:
    ep = int(os.path.basename(f)[3:-5])
    d = json.load(open(f))
    steps = d["steps"]
    teams = d["info"].get("TeamNames", [None, None])
    scores = [team_score.get(t) for t in teams]
    # names from step0 visualize (has full decks w/ names)
    walk_names(steps[0])
    maxturn = 0
    for t in range(len(steps)):
        for seat in range(2):
            cur = steps[t][seat]["observation"].get("current")
            if cur:
                maxturn = max(maxturn, cur.get("turn", 0))
                scan_stacks(cur)
    episodes.append(
        {
            "ep": ep,
            "teams": teams,
            "scores": scores,
            "rewards": d["rewards"],
            "nsteps": len(steps),
            "maxturn": maxturn,
        }
    )

    for t in range(len(steps) - 1):
        for seat in range(2):
            fr = steps[t][seat]
            sel = fr["observation"].get("select")
            if (
                fr["status"] != "ACTIVE"
                or not sel
                or not isinstance(sel.get("option"), list)
            ):
                continue
            act = steps[t + 1][seat]["action"]
            if not isinstance(act, list) or not act:
                continue
            opts = sel["option"]
            cur = fr["observation"].get("current")
            me = cur["yourIndex"] if cur else seat
            chosen = [opts[i] for i in act if isinstance(i, int) and 0 <= i < len(opts)]
            rec = {
                "ep": ep,
                "seat": seat,
                "t": t,
                "team": teams[seat],
                "score": scores[seat],
                "seltype": sel.get("type"),
                "ctx": sel.get("context"),
                "nopt": len(opts),
                "minC": sel.get("minCount"),
                "maxC": sel.get("maxCount"),
                "act": act,
                "opt_types": [o.get("type") for o in opts],
                "chosen_types": [o.get("type") for o in chosen],
                "turn": cur.get("turn") if cur else None,
                "tac": cur.get("turnActionCount") if cur else None,
            }
            # MAIN-decision extras
            if sel.get("context") == CTX_MAIN and cur:
                pl = cur["players"][me]
                hand = pl.get("hand", [])
                # chosen PLAY card id (for item/supporter classification + play mix)
                if len(chosen) == 1 and chosen[0].get("type") == OPT_PLAY:
                    idx = chosen[0].get("index", -1)
                    if 0 <= idx < len(hand):
                        cid = hand[idx]["id"]
                        rec["play_id"] = cid
                        play_votes[cid] += 1
                        nxt = steps[t + 1][seat]["observation"].get("current")
                        if (
                            nxt
                            and not cur.get("supporterPlayed")
                            and nxt.get("supporterPlayed")
                            and nxt.get("turn") == cur.get("turn")
                        ):
                            supporter_votes[cid] += 1
                # attach target
                if len(chosen) == 1 and chosen[0].get("type") == OPT_ATTACH:
                    rec["attach_area"] = chosen[0].get("inPlayArea")
                att_areas = {
                    o.get("inPlayArea") for o in opts if o.get("type") == OPT_ATTACH
                }
                rec["attach_both_legal"] = (
                    AREA_ACTIVE in att_areas and AREA_BENCH in att_areas
                )
                # retreat energy accounting
                if len(chosen) == 1 and chosen[0].get("type") == OPT_RETREAT:
                    active = pl.get("active", [])
                    if active:
                        mon = active[0]
                        e_before = len(mon.get("energyCards", []))
                        serial = mon.get("serial")
                        e_after = None
                        # the retreating mon reaches the bench after optional
                        # CTX_DISCARD_ENERGY(30) selects + CTX_SWITCH(3);
                        # scan forward for its serial on our bench
                        for dt in range(1, 15):
                            if t + dt >= len(steps):
                                break
                            nxt = steps[t + dt][seat]["observation"].get("current")
                            if not nxt:
                                continue
                            me2 = nxt["yourIndex"]
                            hit = [
                                b
                                for b in nxt["players"][me2].get("bench", [])
                                if b.get("serial") == serial
                            ]
                            if hit:
                                e_after = len(hit[0].get("energyCards", []))
                                break
                        retreat_events.append(
                            {
                                "ep": ep,
                                "seat": seat,
                                "t": t,
                                "e_before": e_before,
                                "e_after": e_after,
                            }
                        )
            decisions.append(rec)

# finalize card classes
supporter_ids = {cid for cid, n in supporter_votes.items() if n >= 1}
item_ids = {
    cid
    for cid in play_votes
    if cid not in supporter_ids
    and cid not in pokemon_ids
    and cid not in stadium_ids
    and cid not in energy_ids
    and cid not in tool_ids
}
# name-based energy fallback (deck counting): ids whose name contains 'Energy'
energy_by_name = {i for i, n in id_name.items() if "Energy" in n}


def card_class(cid):
    if cid in pokemon_ids:
        return "POKEMON"
    if cid in supporter_ids:
        return "SUPPORTER"
    if cid in stadium_ids:
        return "STADIUM"
    if cid in energy_ids or cid in energy_by_name:
        return "ENERGY"
    if cid in tool_ids:
        return "TOOL"
    if cid in item_ids:
        return "ITEM"
    return "UNKNOWN"


json.dump(
    {
        "n_ids_named": len(id_name),
        "pokemon": len(pokemon_ids),
        "energy": len(energy_ids | energy_by_name),
        "tool": len(tool_ids),
        "stadium": len(stadium_ids),
        "supporter": sorted(supporter_ids),
        "item": sorted(item_ids),
        "supporter_names": {str(i): id_name.get(i) for i in sorted(supporter_ids)},
        "item_names": {str(i): id_name.get(i) for i in sorted(item_ids)},
    },
    open(os.path.join(OUT, "card_classes.json"), "w"),
    indent=1,
)


# ---------- filters ----------
def is_top(r):
    return r["score"] is not None and r["score"] >= 1100


R = {}  # results

# decision counts under several filters
for name, flt in [
    ("top1100_seats", is_top),
    ("known_seats", lambda r: r["score"] is not None),
    ("all_seats", lambda r: True),
]:
    sub = [r for r in decisions if flt(r)]
    forced = [r for r in sub if r["nopt"] == 1]
    multi = [r for r in sub if r["nopt"] > 1]
    main_multi = [r for r in multi if r["ctx"] == CTX_MAIN]
    # SEL_YES_NO(9) exclusion hypothesis for the spec's 9,267/664 counts
    sub_x = [r for r in sub if r["seltype"] != 9]
    forced_x = [r for r in sub_x if r["nopt"] == 1]
    multi_x = [r for r in sub_x if r["nopt"] > 1]
    R.setdefault("decision_counts", {})[name] = {
        "total": len(sub),
        "forced": len(forced),
        "forced_idx0": sum(1 for r in forced if r["act"] == [0]),
        "multi": len(multi),
        "main_multi": len(main_multi),
        "total_ex_yesno": len(sub_x),
        "forced_ex_yesno": len(forced_x),
        "multi_ex_yesno": len(multi_x),
    }

# strict episodes: both seats >=1100
strict_eps = {
    e["ep"] for e in episodes if all(s is not None and s >= 1100 for s in e["scores"])
}
strict = [r for r in decisions if r["ep"] in strict_eps and is_top(r) and r["nopt"] > 1]
R["strict_both1100"] = {"episodes": len(strict_eps), "multi_decisions": len(strict)}

top_multi = [r for r in decisions if is_top(r) and r["nopt"] > 1]
top_main = [r for r in top_multi if r["ctx"] == CTX_MAIN]

# bucket counts by (seltype, ctx)
buckets = collections.Counter((r["seltype"], r["ctx"]) for r in top_multi)
R["top_buckets_seltype_ctx"] = {f"{k[0]}/{k[1]}": v for k, v in buckets.most_common(20)}

# ---------- ability ----------
ab_avail = [r for r in top_main if OPT_ABILITY in r["opt_types"]]
ab_taken = [r for r in ab_avail if OPT_ABILITY in r["chosen_types"]]
both = [
    r
    for r in top_main
    if OPT_ABILITY in r["opt_types"] and OPT_ATTACK in r["opt_types"]
]
both_ab = [r for r in both if OPT_ABILITY in r["chosen_types"]]
R["ability"] = {
    "main_multi_with_ability": len(ab_avail),
    "ability_taken": len(ab_taken),
    "rate": round(len(ab_taken) / max(1, len(ab_avail)), 4),
    "both_ability_attack_legal": len(both),
    "ability_taken_in_both": len(both_ab),
    "rate_in_both": round(len(both_ab) / max(1, len(both)), 4),
}

# ---------- retreat ----------
ret_legal = [r for r in top_main if OPT_RETREAT in r["opt_types"]]
ret_taken = [r for r in ret_legal if OPT_RETREAT in r["chosen_types"]]
turns_legal = {(r["ep"], r["seat"], r["turn"]) for r in ret_legal}
turns_taken = {(r["ep"], r["seat"], r["turn"]) for r in ret_taken}
top_ep_seat = {(r["ep"], r["seat"]) for r in top_multi}
tre = [e for e in retreat_events if (e["ep"], e["seat"]) in top_ep_seat]
free = [e for e in tre if e["e_after"] is not None and e["e_after"] == e["e_before"]]
tracked = [e for e in tre if e["e_after"] is not None]
R["retreat"] = {
    "decisions_retreat_legal": len(ret_legal),
    "retreat_chosen": len(ret_taken),
    "per_decision_rate": round(len(ret_taken) / max(1, len(ret_legal)), 4),
    "turns_retreat_legal": len(turns_legal),
    "turns_retreated": len(turns_taken),
    "per_turn_rate": round(len(turns_taken) / max(1, len(turns_legal)), 4),
    "retreat_events_tracked": len(tracked),
    "zero_energy_paid": len(free),
    "free_rate": round(len(free) / max(1, len(tracked)), 4),
}

# ---------- energy attach ----------
att = [r for r in top_main if r.get("attach_area") is not None]
att_bench = [r for r in att if r["attach_area"] == AREA_BENCH]
att_both = [r for r in att if r.get("attach_both_legal")]
att_both_bench = [r for r in att_both if r["attach_area"] == AREA_BENCH]
R["energy_attach"] = {
    "attach_chosen": len(att),
    "to_bench": len(att_bench),
    "bench_rate": round(len(att_bench) / max(1, len(att)), 4),
    "both_legal": len(att_both),
    "both_legal_bench": len(att_both_bench),
    "both_legal_bench_rate": round(len(att_both_bench) / max(1, len(att_both)), 4),
}

# ---------- CTX_TO_DECK(9) ----------
td = [r for r in decisions if is_top(r) and r["ctx"] == CTX_TO_DECK]
td_multi_cnt = [r for r in td if (r["maxC"] or 0) > (r["minC"] or 0)]
td_max = [r for r in td_multi_cnt if len(r["act"]) == min(r["maxC"], r["nopt"])]
R["ctx_to_deck"] = {
    "decisions": len(td),
    "count_flexible(min<max)": len(td_multi_cnt),
    "took_effective_max": len(td_max),
    "detail": [
        {
            "ep": r["ep"],
            "min": r["minC"],
            "max": r["maxC"],
            "nopt": r["nopt"],
            "picked": len(r["act"]),
        }
        for r in td_multi_cnt[:50]
    ],
}

# ---------- play mix ----------
mix = collections.Counter(card_class(r["play_id"]) for r in top_main if "play_id" in r)
R["play_mix_top"] = dict(mix)
R["play_mix_item_vs_supporter_ratio"] = round(mix["ITEM"] / max(1, mix["SUPPORTER"]), 3)

# ---------- cadence: mean turnActionCount by chosen main action ----------
cad = collections.defaultdict(list)
for r in top_main:
    if r["tac"] is None or len(r["chosen_types"]) != 1:
        continue
    ct = r["chosen_types"][0]
    if ct == OPT_PLAY and "play_id" in r:
        cad["PLAY_" + card_class(r["play_id"])].append(r["tac"])
    else:
        lbl = {
            OPT_PLAY: "PLAY",
            OPT_ATTACH: "ATTACH",
            OPT_EVOLVE: "EVOLVE",
            OPT_ABILITY: "ABILITY",
            OPT_RETREAT: "RETREAT",
            OPT_ATTACK: "ATTACK",
            OPT_END: "END",
        }.get(ct, f"T{ct}")
        cad[lbl].append(r["tac"])
R["cadence_mean_tac"] = {
    k: {"n": len(v), "mean": round(statistics.mean(v), 2)}
    for k, v in sorted(cad.items())
    if v
}

# ---------- action mix over top MAIN decisions ----------
amix = collections.Counter(
    r["chosen_types"][0] for r in top_main if len(r["chosen_types"]) == 1
)
R["main_action_mix_top"] = {str(k): v for k, v in amix.most_common()}

# ---------- bench ----------
bench_stats = {}
for f in files:
    ep = int(os.path.basename(f)[3:-5])
    d = json.load(open(f))
    steps = d["steps"]
    teams = d["info"].get("TeamNames", [None, None])
    for seat in range(2):
        sc = team_score.get(teams[seat])
        if sc is None or sc < 1100:
            continue
        mx, at_t3 = 0, None
        for t in range(len(steps)):
            cur = steps[t][seat]["observation"].get("current")
            if not cur:
                continue
            me = cur["yourIndex"]
            b = len(cur["players"][me].get("bench", []))
            mx = max(mx, b)
            if cur.get("turn") == 3:
                at_t3 = b  # last obs at turn 3
        bench_stats[(ep, seat)] = (mx, at_t3)
full5 = sum(1 for mx, _ in bench_stats.values() if mx >= 5)
t3 = [v for _, v in bench_stats.values() if v is not None]
R["bench"] = {
    "seat_games": len(bench_stats),
    "ever_full5": full5,
    "full5_rate": round(full5 / max(1, len(bench_stats)), 4),
    "mean_bench_end_turn3": round(statistics.mean(t3), 2) if t3 else None,
    "n_turn3_obs": len(t3),
}

# ---------- deck energy ----------
deck_energy = []
seen_decks = set()
for f in files:
    ep = int(os.path.basename(f)[3:-5])
    d = json.load(open(f))
    teams = d["info"].get("TeamNames", [None, None])
    for seat in range(2):
        sc = team_score.get(teams[seat])
        if sc is None or sc < 1100:
            continue
        deck = d["steps"][1][seat]["action"]
        if not isinstance(deck, list) or len(deck) != 60:
            continue
        key = (teams[seat], tuple(sorted(deck)))
        ne = sum(1 for c in deck if c in energy_ids or c in energy_by_name)
        deck_energy.append(
            {
                "team": teams[seat],
                "ep": ep,
                "n_energy": ne,
                "new_deck": key not in seen_decks,
            }
        )
        seen_decks.add(key)
uniq = [de["n_energy"] for de in deck_energy if de["new_deck"]]
R["deck_energy"] = {
    "seat_decks": len(deck_energy),
    "unique_team_decks": len(uniq),
    "mean_energy_unique": round(statistics.mean(uniq), 2) if uniq else None,
    "per_unique_deck": sorted(uniq),
}

# ---------- game length ----------
ns = [e["nsteps"] for e in episodes]
mt = [e["maxturn"] for e in episodes]
R["game_length"] = {
    "n_episodes": len(episodes),
    "steps_mean": round(statistics.mean(ns), 1),
    "steps_median": statistics.median(ns),
    "steps_min": min(ns),
    "steps_max": max(ns),
    "turns_mean": round(statistics.mean(mt), 1),
    "turns_median": statistics.median(mt),
    "turns_min": min(mt),
    "turns_max": max(mt),
}

# ---------- rewards vs rating ----------
rows = []
for e in episodes:
    s0, s1 = e["scores"]
    if s0 is not None and s1 is not None and e["rewards"] and None not in e["rewards"]:
        hi = 0 if s0 >= s1 else 1
        if abs(s0 - s1) > 1e-9:
            rows.append(
                {
                    "ep": e["ep"],
                    "diff": abs(s0 - s1),
                    "hi_won": e["rewards"][hi] > e["rewards"][1 - hi],
                    "drawish": e["rewards"][0] == e["rewards"][1],
                }
            )
hi_w = sum(1 for r in rows if r["hi_won"])
top_seat_rewards = []
for e in episodes:
    for seat in range(2):
        sc = e["scores"][seat]
        if (
            sc is not None
            and sc >= 1100
            and e["rewards"]
            and e["rewards"][seat] is not None
        ):
            top_seat_rewards.append(e["rewards"][seat])
R["rewards_vs_rating"] = {
    "both_rated_games": len(rows),
    "higher_rated_won": hi_w,
    "higher_rated_winrate": round(hi_w / max(1, len(rows)), 3),
    "top1100_seat_games": len(top_seat_rewards),
    "top1100_mean_reward": round(statistics.mean(top_seat_rewards), 3)
    if top_seat_rewards
    else None,
    "top1100_winrate": round(
        sum(1 for x in top_seat_rewards if x > 0) / max(1, len(top_seat_rewards)), 3
    ),
}

# ---------- actions per turn ----------
per_turn = collections.defaultdict(int)
for r in top_main:
    if r["tac"] is not None:
        per_turn[(r["ep"], r["seat"], r["turn"])] = max(
            per_turn[(r["ep"], r["seat"], r["turn"])], r["tac"]
        )
apt = list(per_turn.values())
R["actions_per_turn_top"] = (
    {
        "turns": len(apt),
        "mean_max_tac": round(statistics.mean(apt), 2),
        "median": statistics.median(apt),
    }
    if apt
    else {}
)

json.dump(R, open(os.path.join(OUT, "replay_quant_results.json"), "w"), indent=1)
print(json.dumps(R, indent=1))
