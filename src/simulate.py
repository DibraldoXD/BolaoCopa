"""
Feature 08 — Monte Carlo: simulação do torneio

Simula a Copa 2026 N=1000 vezes (seed=42), agrega probabilidades por fase/seleção
e grava gold_probabilidades_copa (48 linhas).
"""

import io
import re
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

from src.pg_conn import get_engine, get_raw_connection
from src.predict import carregar_artefatos, prever_jogo

N_SIMS = 1000
SEED = 42

# R32 slots com terceiros — match_id → set de grupos elegíveis
TERCEIROS_SLOTS = {
    "M74": set("ABCDF"),
    "M77": set("CDFGH"),
    "M79": set("CEFHI"),
    "M80": set("EHIJK"),
    "M81": set("BEFIJ"),
    "M82": set("AEHIJ"),
    "M85": set("EFGIJ"),
    "M87": set("DEIJL"),
}

# round → fase numérica acumulada (sem "3rd" — não conta para ranking de fase)
ROUND_TO_PHASE = {"R32": 2, "R16": 3, "QF": 4, "SF": 5, "Final": 6}

CREATE_SQL = """
CREATE TABLE gold_probabilidades_copa (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    selecao      TEXT,
    prob_grupo   DOUBLE PRECISION,
    prob_oitavas DOUBLE PRECISION,
    prob_quartas DOUBLE PRECISION,
    prob_semi    DOUBLE PRECISION,
    prob_final   DOUBLE PRECISION,
    prob_campea  DOUBLE PRECISION
);
"""


def carregar_dados(elo_dict, modelo_casa, modelo_visit):
    grupos_df  = pd.read_csv("data/grupos_copa2026.csv")
    calendario = pd.read_csv("data/calendario_copa2026.csv")
    copa_jogos = pd.read_sql("SELECT * FROM silver_copa2026 ORDER BY data, id", get_engine())

    grupos_por_grupo = {g: list(df["nation"]) for g, df in grupos_df.groupby("group")}

    grupo_lambdas = {}
    for row in copa_jogos.itertuples(index=False):
        p = prever_jogo(row.time_casa, row.time_visitante, row.neutro, 3,
                        elo_dict, modelo_casa, modelo_visit)
        grupo_lambdas[(row.time_casa, row.time_visitante)] = (
            p["gols_esperados_casa"], p["gols_esperados_visitante"]
        )

    return grupos_por_grupo, calendario, copa_jogos, grupo_lambdas


def assign_thirds(selected_thirds):
    """selected_thirds: [(group, team), ...] com 8 elementos. Retorna {match_id: team}."""
    slot_keys  = list(TERCEIROS_SLOTS)
    group_list = [g for g, _ in selected_thirds]
    teams_map  = {g: t for g, t in selected_thirds}

    cost = np.full((8, 8), 1000)
    for i, g in enumerate(group_list):
        for j, mid in enumerate(slot_keys):
            if g in TERCEIROS_SLOTS[mid]:
                cost[i, j] = 0

    ri, ci = linear_sum_assignment(cost)
    return {slot_keys[j]: teams_map[group_list[i]] for i, j in zip(ri, ci)}


def resolve_slot(slot_str, slots, terceiros_match, match_id):
    if re.match(r"^\d[A-L]$", slot_str):
        return slots[slot_str]
    elif slot_str.startswith("3"):
        return terceiros_match[match_id]
    elif slot_str.startswith("W") or slot_str.startswith("RU"):
        return slots[slot_str]
    raise ValueError(f"Slot desconhecido: {slot_str!r}")


def simulate_once(rng, grupos_por_grupo, copa_jogos, calendario,
                  grupo_lambdas, lambda_cache, elo_dict, modelo_casa, modelo_visit):
    time_to_grupo = {t: g for g, teams in grupos_por_grupo.items() for t in teams}

    # --- Fase de grupos ---
    stats = {
        g: {t: {"pts": 0, "gd": 0, "gf": 0} for t in teams}
        for g, teams in grupos_por_grupo.items()
    }
    for row in copa_jogos.itertuples(index=False):
        lc, lv = grupo_lambdas[(row.time_casa, row.time_visitante)]
        gc = int(rng.poisson(lc))
        gv = int(rng.poisson(lv))
        g  = time_to_grupo[row.time_casa]

        if gc > gv:
            stats[g][row.time_casa]["pts"] += 3
        elif gc == gv:
            stats[g][row.time_casa]["pts"] += 1
            stats[g][row.time_visitante]["pts"] += 1
        else:
            stats[g][row.time_visitante]["pts"] += 3

        stats[g][row.time_casa]["gd"]      += gc - gv
        stats[g][row.time_visitante]["gd"] += gv - gc
        stats[g][row.time_casa]["gf"]      += gc
        stats[g][row.time_visitante]["gf"] += gv

    # --- Classificar grupos ---
    slots   = {}
    thirds  = {}  # group → (team, pts, gd, gf)

    for g, grp_stats in stats.items():
        tiebreak = {t: rng.random() for t in grp_stats}
        ranked = sorted(
            grp_stats.items(),
            key=lambda x: (-x[1]["pts"], -x[1]["gd"], -x[1]["gf"], tiebreak[x[0]])
        )
        slots[f"1{g}"] = ranked[0][0]
        slots[f"2{g}"] = ranked[1][0]
        thirds[g] = (ranked[2][0], ranked[2][1]["pts"], ranked[2][1]["gd"], ranked[2][1]["gf"])

    # --- 8 melhores terceiros ---
    tiebreak3 = {g: rng.random() for g in thirds}
    sorted_thirds = sorted(
        thirds.items(),
        key=lambda x: (-x[1][1], -x[1][2], -x[1][3], tiebreak3[x[0]])
    )
    top8 = [(g, info[0]) for g, info in sorted_thirds[:8]]
    terceiros_match = assign_thirds(top8)

    # --- Fase atingida por cada seleção ---
    reached = {}
    for g in grupos_por_grupo:
        reached[slots[f"1{g}"]] = 1
        reached[slots[f"2{g}"]] = 1
    for team in terceiros_match.values():
        reached[team] = 1

    # --- Mata-mata ---
    for row in calendario.itertuples(index=False):
        round_ = getattr(row, "round")
        mid    = row.match_id           # "M73"
        mid_num = mid[1:]               # "73"

        home = resolve_slot(row.home_slot, slots, terceiros_match, mid)
        away = resolve_slot(row.away_slot, slots, terceiros_match, mid)

        key = (home, away)
        if key not in lambda_cache:
            p = prever_jogo(home, away, True, 3, elo_dict, modelo_casa, modelo_visit)
            lambda_cache[key] = (p["gols_esperados_casa"], p["gols_esperados_visitante"])
        lc, lv = lambda_cache[key]

        gc = int(rng.poisson(lc))
        gv = int(rng.poisson(lv))

        if gc > gv:
            winner, loser = home, away
        elif gv > gc:
            winner, loser = away, home
        else:
            winner, loser = (home, away) if rng.random() < 0.5 else (away, home)

        slots[f"W{mid_num}"] = winner
        if round_ == "SF":
            slots[f"RU{mid_num}"] = loser

        if round_ in ROUND_TO_PHASE:
            reached[winner] = ROUND_TO_PHASE[round_]

    return reached


def run_monte_carlo(grupos_por_grupo, copa_jogos, calendario, grupo_lambdas,
                    elo_dict, modelo_casa, modelo_visit):
    rng = np.random.default_rng(SEED)
    lambda_cache = {}
    counts = defaultdict(lambda: [0] * 7)  # counts[team][phase], índices 1–6

    for i in range(N_SIMS):
        if (i + 1) % 100 == 0:
            print(f"  Simulação {i+1}/{N_SIMS} ...")
        reached = simulate_once(
            rng, grupos_por_grupo, copa_jogos, calendario,
            grupo_lambdas, lambda_cache, elo_dict, modelo_casa, modelo_visit
        )
        for team, phase in reached.items():
            for p in range(1, phase + 1):
                counts[team][p] += 1

    print(f"  Lambda cache: {len(lambda_cache)} pares únicos.")
    return counts


def build_output(counts, grupos_por_grupo) -> pd.DataFrame:
    all_teams = [t for teams in grupos_por_grupo.values() for t in teams]
    rows = []
    for team in all_teams:
        c = counts[team]
        rows.append({
            "selecao":      team,
            "prob_grupo":   c[1] / N_SIMS,
            "prob_oitavas": c[2] / N_SIMS,
            "prob_quartas": c[3] / N_SIMS,
            "prob_semi":    c[4] / N_SIMS,
            "prob_final":   c[5] / N_SIMS,
            "prob_campea":  c[6] / N_SIMS,
        })
    return (
        pd.DataFrame(rows)
        .sort_values("prob_campea", ascending=False)
        .reset_index(drop=True)
    )


def load_to_db(df: pd.DataFrame) -> None:
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS gold_probabilidades_copa;")
            cur.execute(CREATE_SQL)
            buf = io.StringIO()
            df.to_csv(buf, index=False, na_rep="")
            buf.seek(0)
            cols = ", ".join(df.columns)
            cur.copy_expert(
                f"COPY gold_probabilidades_copa ({cols}) FROM STDIN "
                f"WITH (FORMAT CSV, HEADER TRUE, NULL '')",
                buf,
            )
        conn.commit()
        print(f"Tabela gold_probabilidades_copa criada com {len(df)} linhas.")
    finally:
        conn.close()


def main() -> None:
    print("Carregando modelos e ELO ...")
    modelo_casa, modelo_visit, elo_dict = carregar_artefatos()

    print("Carregando dados do torneio ...")
    grupos_por_grupo, calendario, copa_jogos, grupo_lambdas = carregar_dados(
        elo_dict, modelo_casa, modelo_visit
    )

    print(f"Rodando {N_SIMS} simulações (seed={SEED}) ...")
    counts = run_monte_carlo(
        grupos_por_grupo, copa_jogos, calendario, grupo_lambdas,
        elo_dict, modelo_casa, modelo_visit
    )

    df = build_output(counts, grupos_por_grupo)

    print("\nTop 10 favoritas ao título:")
    print(df[["selecao", "prob_campea"]].head(10).to_string(index=False))

    total_campea = df["prob_campea"].sum()
    total_grupo  = df["prob_grupo"].sum()
    print(f"\nSoma prob_campea: {total_campea*100:.1f}%  (esperado ~100%)")
    print(f"Soma prob_grupo:  {total_grupo:.1f}  (esperado ~32)")

    load_to_db(df)


if __name__ == "__main__":
    main()
