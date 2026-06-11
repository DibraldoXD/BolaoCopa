"""
Módulo de previsão de partida para o dashboard (flat imports — compatível com sys.path src/).

Reimplementa a lógica de predict.py sem 'from src.X import'.
"""

import pickle

import numpy as np
import pandas as pd
import statsmodels.api as sm

from pg_conn import get_engine
from poisson import probabilidades_resultado

PESO_TORNEIO_COPA = 3
FEATURES = ["elo_casa", "elo_visitante", "dif_elo", "neutro", "peso_torneio", "peso_recencia"]


def carregar_modelos() -> tuple:
    """Carrega os pkl treinados e o dicionário de ELO atual. Use com @st.cache_resource."""
    mc = pickle.load(open("models/modelo_poisson_casa.pkl",      "rb"))
    mv = pickle.load(open("models/modelo_poisson_visitante.pkl", "rb"))
    elo_df   = pd.read_sql("SELECT selecao, elo FROM silver_elo_atual", get_engine())
    elo_dict = dict(zip(elo_df["selecao"], elo_df["elo"]))
    return mc, mv, elo_dict


def prever_jogo(
    time_casa: str,
    time_visitante: str,
    neutro: bool,
    peso_torneio: int,
    elo_dict: dict,
    mc,
    mv,
) -> dict:
    """Retorna λ e probabilidades V/E/D para um confronto."""
    ec, ev = elo_dict[time_casa], elo_dict[time_visitante]
    X = sm.add_constant(
        pd.DataFrame([{
            "elo_casa":      ec,
            "elo_visitante": ev,
            "dif_elo":       ec - ev,
            "neutro":        int(neutro),
            "peso_torneio":  peso_torneio,
            "peso_recencia": 1.0,
        }]),
        has_constant="add",
    )
    lc = float(mc.predict(X).iloc[0])
    lv = float(mv.predict(X).iloc[0])
    pv, pe, pd_ = probabilidades_resultado(lc, lv)
    return {
        "gols_esperados_casa":      lc,
        "gols_esperados_visitante": lv,
        "prob_vitoria":  pv,
        "prob_empate":   pe,
        "prob_derrota":  pd_,
    }
