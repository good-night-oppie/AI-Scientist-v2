"""Seed: working PTCG baseline agent + evaluation contract for the cabt simulator.

Self-contained. Requires only `kaggle-environments` (installed). Every game decision:
the engine passes obs with obs['select'] = {'type','context','minCount','maxCount',
'option': [...]} listing ONLY legal options; return a list of option indices (top-k,
k=maxCount usually). First call has obs['select'] is None -> return the 60-card DECK.
obs['current'] holds visible state: turn, yourIndex, players[2] with active/bench
(each Pokemon: id, hp, maxHp, energies, tools), own hand (card ids), handCount,
deckCount, prize (nulls = face-down), discard, status flags. obs['logs'] = event log.

Engine option/select/area/context integer codes are in the constants below.
Card database: AllCard()/AllAttack() ctypes calls below return every card and attack
(name, hp, cardType 0=Pokemon 1=Item 2=Tool 3=Supporter 4=Stadium 5/6=Energy,
attacks: attackId list; attack: name, text, damage, energies cost list,
weakness/resistance on cards, evolvesFrom chain).
"""

import ctypes
import json
import random
from functools import lru_cache

import numpy as np

# ---------- select/option/area/context codes (cabt engine) ----------
SEL_MAIN, SEL_CARD, SEL_YES_NO, SEL_COUNT = 0, 1, 9, 8
OPT_NUMBER, OPT_YES, OPT_NO, OPT_CARD = 0, 1, 2, 3
OPT_PLAY, OPT_ATTACH, OPT_EVOLVE, OPT_ABILITY = 7, 8, 9, 10
OPT_RETREAT, OPT_ATTACK, OPT_END = 12, 13, 14
AREA_HAND, AREA_ACTIVE, AREA_BENCH, AREA_LOOKING = 2, 4, 5, 12
CTX_HEAL, CTX_DAMAGE, CTX_DISCARD = 17, 15, 8
SELF_LOSS_CTX = {8, 9, 10, 11, 23, 26, 27, 29, 30, 32}
SELF_GAIN_CTX = {16, 17, 48}
DAMAGE_CTX = {13, 14, 15}

# ---------- known-legal 60-card deck (Kyogre / Mega Abomasnow ex, water) ----------
DECK = [
    721,
    721,
    722,
    722,
    722,
    722,
    723,
    723,
    723,
    723,
    1092,
    1121,
    1121,
    1145,
    1145,
    1163,
    1163,
    1219,
    1219,
    1219,
    1219,
    1227,
    1227,
    1227,
    1227,
    1262,
    1262,
] + [3] * 33


# ---------- card database straight from the engine ----------
@lru_cache(maxsize=1)
def card_db():
    from kaggle_environments.envs.cabt.cg.sim import lib

    lib.AllCard.restype = ctypes.c_char_p
    lib.AllCard.argtypes = []
    lib.AllAttack.restype = ctypes.c_char_p
    lib.AllAttack.argtypes = []
    cards = {c["cardId"]: c for c in json.loads(lib.AllCard().decode())}
    attacks = {a["attackId"]: a for a in json.loads(lib.AllAttack().decode())}
    return cards, attacks


def attack_damage(attack_id):
    a = card_db()[1].get(attack_id)
    return int(a["damage"]) if a else 0


# ---------- baseline heuristic policy (improve me) ----------
MAIN_SCORES = {
    OPT_EVOLVE: 80.0,
    OPT_ATTACH: 70.0,
    OPT_PLAY: 50.0,
    OPT_ATTACK: 30.0,
    OPT_ABILITY: 25.0,
    OPT_END: 1.0,
    OPT_RETREAT: 0.0,
}


def _score_main(opt, cur, me):
    t = opt.get("type")
    s = MAIN_SCORES.get(t, 20.0)
    if t == OPT_ATTACK:
        dmg = attack_damage(opt.get("attackId", 0))
        s += dmg / 1000.0
        try:  # lethal attack outranks all setup
            if dmg >= cur["players"][1 - me]["active"][0]["hp"] > 0:
                s = 95.0 + dmg / 1000.0
        except (IndexError, KeyError, TypeError):
            pass
    elif t == OPT_ATTACH and opt.get("inPlayArea") == AREA_ACTIVE:
        s += 2.0
    elif t == OPT_PLAY and cur is not None:
        try:
            cid = cur["players"][me]["hand"][opt.get("index", 0)]["id"]
            c = card_db()[0][cid]
            if c["cardType"] == 0 and c.get("basic"):
                s = 66.0 if len(cur["players"][me]["bench"]) < 3 else 45.0
            elif c["cardType"] == 3:
                s = 55.0
        except (IndexError, KeyError, TypeError):
            pass
    return s


def _score_card(opt, ctx, cur, me):
    p_idx, area, idx = (
        opt.get("playerIndex", me),
        opt.get("area", 0),
        opt.get("index", 0),
    )
    poke = None
    try:
        p = cur["players"][p_idx]
        poke = (
            p["active"][idx]
            if area == AREA_ACTIVE
            else (p["bench"][idx] if area == AREA_BENCH else None)
        )
    except (IndexError, KeyError, TypeError):
        pass
    if ctx in DAMAGE_CTX and poke is not None:
        return (100.0 - poke.get("hp", 0)) if p_idx != me else poke.get("hp", 0) / 10.0
    if ctx in SELF_GAIN_CTX and poke is not None:
        return float(poke.get("maxHp", 0) - poke.get("hp", 0))
    if poke is not None:
        return float(poke.get("hp", 0))
    return 0.0


def choose(obs):
    sel = obs.get("select")
    if sel is None:
        return list(DECK)
    options = sel.get("option") or []
    if not options:
        return []
    cur = obs.get("current")
    me = cur["yourIndex"] if cur else 0
    stype, ctx = sel.get("type", 0), sel.get("context", 0)

    def score(i, o):
        t = o.get("type")
        if stype == SEL_MAIN:
            return _score_main(o, cur, me)
        if t == OPT_YES:
            return 1.0
        if t == OPT_NO:
            return 0.0
        if t == OPT_NUMBER:
            return float(o.get("number", 0))
        if t == OPT_ATTACK:
            return float(attack_damage(o.get("attackId", 0)))
        return _score_card(o, ctx, cur, me)

    ranked = sorted(range(len(options)), key=lambda i: (-score(i, options[i]), i))
    k = min(sel.get("maxCount", 1), len(options))
    if ctx in SELF_LOSS_CTX and sel.get("minCount", 1) < sel.get("maxCount", 1):
        k = max(sel.get("minCount", 0), 0)
    return ranked[:k]


def agent(obs):
    """NEVER raises: an exception forfeits the game."""
    try:
        return choose(obs)
    except Exception:
        sel = obs.get("select")
        if sel is None:
            return list(DECK)
        return list(range(min(sel.get("maxCount", 1), len(sel.get("option") or []))))


# ---------- evaluation contract (metric: mean winrate, higher is better) ----------
def evaluate(n_games_per_opponent=80, seed=0):
    from kaggle_environments import make

    random.seed(seed)
    np.random.seed(seed)
    experiment_data = {}
    for opponent in ("random", "first"):
        wins, curve = [], []
        for g in range(n_games_per_opponent):
            seat = g % 2  # alternate seats to cancel first-player advantage
            env = make("cabt")
            env.run([agent, opponent] if seat == 0 else [opponent, agent])
            w = 1 if env.state[seat].reward == 1 else 0
            wins.append(w)
            curve.append(sum(wins) / len(wins))
        experiment_data[f"vs_{opponent}"] = {
            "wins": wins,
            "winrate_curve": curve,
            "final_winrate": curve[-1],
        }
    experiment_data["mean_winrate"] = float(
        np.mean(
            [experiment_data[k]["final_winrate"] for k in ("vs_random", "vs_first")]
        )
    )
    np.save("working/experiment_data.npy", experiment_data)  # required artifact
    return experiment_data


if __name__ == "__main__":
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = evaluate(n_games_per_opponent=80, seed=0)
    fig, ax = plt.subplots()
    for k in ("vs_random", "vs_first"):
        ax.plot(
            data[k]["winrate_curve"],
            label=f"{k} (final {data[k]['final_winrate']:.2f})",
        )
    ax.set_xlabel("games played"), ax.set_ylabel("cumulative winrate")
    ax.set_title(f"PTCG baseline — mean winrate {data['mean_winrate']:.3f}")
    ax.legend(), ax.grid(True)
    fig.savefig("working/winrate_curves.png", dpi=120)
    print("mean_winrate:", data["mean_winrate"])
