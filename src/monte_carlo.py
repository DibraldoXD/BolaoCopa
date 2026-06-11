"""
Módulo Monte Carlo para o dashboard (flat imports — compatível com sys.path src/).

Expõe preparar() e simular_torneio_detalhado() para uso no Streamlit.
"""

import re

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from pg_conn import get_engine
from previsao import carregar_modelos, prever_jogo

NOMES_RODADA = {
    "R32":   "32-avos de final",
    "R16":   "Oitavas de final",
    "QF":    "Quartas de final",
    "SF":    "Semifinais",
    "3rd":   "3º lugar",
    "Final": "Final",
}

slots_terceiros: dict[str, set[str]] = {
    "M74": set("ABCDF"),
    "M77": set("CDFGH"),
    "M79": set("CEFHI"),
    "M80": set("EHIJK"),
    "M81": set("BEFIJ"),
    "M82": set("AEHIJ"),
    "M85": set("EFGIJ"),
    "M87": set("DEIJL"),
}

_ROUND_TO_PHASE = {"R32": 2, "R16": 3, "QF": 4, "SF": 5, "Final": 6}


def preparar() -> dict:
    """Carrega todos os dados estáticos do torneio. Use com @st.cache_resource."""
    mc, mv, elo_dict = carregar_modelos()

    grupos_df  = pd.read_csv("data/grupos_copa2026.csv")
    calendario = pd.read_csv("data/calendario_copa2026.csv")
    copa_jogos = pd.read_sql("SELECT * FROM silver_copa2026 ORDER BY data, id", get_engine())

    grupos_por_grupo = {g: list(df["nation"]) for g, df in grupos_df.groupby("group")}
    time_to_grupo    = {t: g for g, teams in grupos_por_grupo.items() for t in teams}

    grupo_lambdas: dict[tuple, tuple] = {}
    for row in copa_jogos.itertuples(index=False):
        p = prever_jogo(row.time_casa, row.time_visitante, row.neutro, 3, elo_dict, mc, mv)
        grupo_lambdas[(row.time_casa, row.time_visitante)] = (
            p["gols_esperados_casa"], p["gols_esperados_visitante"]
        )

    return {
        "mc": mc, "mv": mv, "elo_dict": elo_dict,
        "grupos_por_grupo": grupos_por_grupo,
        "time_to_grupo":    time_to_grupo,
        "calendario":       calendario,
        "copa_jogos":       copa_jogos,
        "grupo_lambdas":    grupo_lambdas,
        "lambda_cache":     {},
    }


def _assign_thirds(selected_thirds: list[tuple]) -> dict[str, str]:
    slot_keys  = list(slots_terceiros)
    group_list = [g for g, _ in selected_thirds]
    teams_map  = {g: t for g, t in selected_thirds}
    cost = np.full((8, 8), 1000)
    for i, g in enumerate(group_list):
        for j, mid in enumerate(slot_keys):
            if g in slots_terceiros[mid]:
                cost[i, j] = 0
    ri, ci = linear_sum_assignment(cost)
    return {slot_keys[j]: teams_map[group_list[i]] for i, j in zip(ri, ci)}


def _resolve_slot(slot_str: str, slots: dict, terceiros_match: dict, match_id: str) -> str:
    if re.match(r"^\d[A-L]$", slot_str):
        return slots[slot_str]
    if slot_str.startswith("3"):
        return terceiros_match[match_id]
    if slot_str.startswith("W") or slot_str.startswith("RU"):
        return slots[slot_str]
    raise ValueError(f"Slot desconhecido: {slot_str!r}")


def simular_torneio_detalhado(preparado: dict, seed=None) -> dict:
    """
    Roda UMA simulação completa. seed=None → aleatório a cada chamada.
    Retorna dict com campea/vice/terceiro, grupos (classificacao+jogos), mata_mata por rodada.
    """
    mc             = preparado["mc"]
    mv             = preparado["mv"]
    elo_dict       = preparado["elo_dict"]
    grupos_por_grupo = preparado["grupos_por_grupo"]
    time_to_grupo  = preparado["time_to_grupo"]
    calendario     = preparado["calendario"]
    copa_jogos     = preparado["copa_jogos"]
    grupo_lambdas  = preparado["grupo_lambdas"]
    lambda_cache   = preparado["lambda_cache"]

    rng = np.random.default_rng(seed)

    # ── Fase de grupos ────────────────────────────────────────────────────────
    stats = {
        g: {t: {"pts": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0} for t in teams}
        for g, teams in grupos_por_grupo.items()
    }
    grupo_jogos: dict[str, list] = {g: [] for g in grupos_por_grupo}

    for row in copa_jogos.itertuples(index=False):
        lc, lv = grupo_lambdas[(row.time_casa, row.time_visitante)]
        gc = int(rng.poisson(lc))
        gv = int(rng.poisson(lv))
        g  = time_to_grupo[row.time_casa]

        grupo_jogos[g].append((row.time_casa, row.time_visitante, gc, gv))
        s_c = stats[g][row.time_casa]
        s_v = stats[g][row.time_visitante]

        s_c["gf"] += gc;  s_c["ga"] += gv
        s_v["gf"] += gv;  s_v["ga"] += gc

        if gc > gv:
            s_c["pts"] += 3;  s_c["w"] += 1;  s_v["l"] += 1
        elif gc == gv:
            s_c["pts"] += 1;  s_c["d"] += 1
            s_v["pts"] += 1;  s_v["d"] += 1
        else:
            s_v["pts"] += 3;  s_v["w"] += 1;  s_c["l"] += 1

    # ── Classificar grupos ────────────────────────────────────────────────────
    slots: dict[str, str] = {}
    thirds: dict[str, tuple] = {}
    result_grupos: dict[str, dict] = {}

    for g, grp in stats.items():
        tb = {t: rng.random() for t in grp}
        ranked = sorted(
            grp.items(),
            key=lambda x: (-x[1]["pts"], -(x[1]["gf"] - x[1]["ga"]), -x[1]["gf"], tb[x[0]])
        )
        slots[f"1{g}"] = ranked[0][0]
        slots[f"2{g}"] = ranked[1][0]
        t3, s3 = ranked[2]
        thirds[g] = (t3, s3["pts"], s3["gf"] - s3["ga"], s3["gf"])

        classificacao = [
            {
                "posicao":     pos,
                "selecao":     team,
                "jogos":       s["w"] + s["d"] + s["l"],
                "vitorias":    s["w"],
                "empates":     s["d"],
                "derrotas":    s["l"],
                "gols_pro":    s["gf"],
                "gols_contra": s["ga"],
                "saldo_gols":  s["gf"] - s["ga"],
                "pontos":      s["pts"],
            }
            for pos, (team, s) in enumerate(ranked, 1)
        ]
        result_grupos[g] = {
            "classificacao": pd.DataFrame(classificacao),
            "jogos":         grupo_jogos[g],
        }

    # ── Top 8 terceiros + matching ────────────────────────────────────────────
    tb3 = {g: rng.random() for g in thirds}
    sorted_thirds = sorted(
        thirds.items(),
        key=lambda x: (-x[1][1], -x[1][2], -x[1][3], tb3[x[0]])
    )
    top8 = [(g, info[0]) for g, info in sorted_thirds[:8]]
    terceiros_match = _assign_thirds(top8)

    # ── Mata-mata ─────────────────────────────────────────────────────────────
    mata_mata: dict[str, list] = {r: [] for r in NOMES_RODADA}
    campea = vice = terceiro = None

    for row in calendario.itertuples(index=False):
        round_ = getattr(row, "round")
        mid    = row.match_id
        mid_num = mid[1:]

        home = _resolve_slot(row.home_slot, slots, terceiros_match, mid)
        away = _resolve_slot(row.away_slot, slots, terceiros_match, mid)

        key = (home, away)
        if key not in lambda_cache:
            p = prever_jogo(home, away, True, 3, elo_dict, mc, mv)
            lambda_cache[key] = (p["gols_esperados_casa"], p["gols_esperados_visitante"])
        lc, lv = lambda_cache[key]

        gc = int(rng.poisson(lc))
        gv = int(rng.poisson(lv))
        penaltis = gc == gv

        if gc > gv:
            winner, loser = home, away
        elif gv > gc:
            winner, loser = away, home
        else:
            winner, loser = (home, away) if rng.random() < 0.5 else (away, home)

        mata_mata[round_].append({
            "home": home, "away": away,
            "gc": gc, "gv": gv,
            "penaltis": penaltis,
            "vencedor": winner,
        })

        slots[f"W{mid_num}"] = winner
        if round_ == "SF":
            slots[f"RU{mid_num}"] = loser

        if round_ == "Final":
            campea, vice = winner, loser
        elif round_ == "3rd":
            terceiro = winner

    return {
        "campea":    campea,
        "vice":      vice,
        "terceiro":  terceiro,
        "grupos":    result_grupos,
        "mata_mata": mata_mata,
    }
