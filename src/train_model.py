"""
Feature 06 — Treino Poisson + validação

Lê gold_atributos, treina dois GLM Poisson (mandante/visitante) com split
temporal 2024-01-01, valida e salva modelos em models/ + metricas_validacao.
"""

import datetime
import pathlib
import pickle

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.pg_conn import get_engine, get_raw_connection
from src.poisson import resultado_previsto, resultado_real

FEATURES = ["elo_casa", "elo_visitante", "dif_elo", "neutro", "peso_torneio", "peso_recencia"]
CORTE = datetime.date(2024, 1, 1)

CREATE_METRICAS = """
CREATE TABLE metricas_validacao (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mae_casa      DOUBLE PRECISION,
    mae_visitante DOUBLE PRECISION,
    acuracia      DOUBLE PRECISION
);
"""


def read_gold() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM gold_atributos ORDER BY data, jogo_id", get_engine())


def montar_X(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].copy()
    X["neutro"] = X["neutro"].astype(int)
    return sm.add_constant(X, has_constant="add")


def treinar(treino: pd.DataFrame):
    X = montar_X(treino)
    pesos = treino["peso_torneio"] * treino["peso_recencia"]
    familia = sm.families.Poisson()

    modelo_casa = sm.GLM(
        treino["gols_casa"], X, family=familia, var_weights=pesos
    ).fit()
    modelo_visit = sm.GLM(
        treino["gols_visitante"], X, family=familia, var_weights=pesos
    ).fit()
    return modelo_casa, modelo_visit


def validar(teste: pd.DataFrame, modelo_casa, modelo_visit) -> tuple[float, float, float]:
    X_teste = montar_X(teste)
    lc = modelo_casa.predict(X_teste)
    lv = modelo_visit.predict(X_teste)

    mae_casa = float(np.abs(lc - teste["gols_casa"].astype(float)).mean())
    mae_visitante = float(np.abs(lv - teste["gols_visitante"].astype(float)).mean())

    prev = [resultado_previsto(c, v) for c, v in zip(lc, lv)]
    reais = [resultado_real(gc, gv) for gc, gv in zip(teste["gols_casa"], teste["gols_visitante"])]
    acuracia = float(np.mean([p == r for p, r in zip(prev, reais)]))

    return mae_casa, mae_visitante, acuracia


def salvar_modelos(modelo_casa, modelo_visit) -> None:
    pathlib.Path("models").mkdir(exist_ok=True)
    pickle.dump(modelo_casa,  open("models/modelo_poisson_casa.pkl",      "wb"))
    pickle.dump(modelo_visit, open("models/modelo_poisson_visitante.pkl", "wb"))
    pickle.dump(FEATURES,     open("models/colunas_atributos.pkl",        "wb"))
    print("Modelos salvos em models/")


def gravar_metricas(mae_casa: float, mae_visitante: float, acuracia: float) -> None:
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS metricas_validacao;")
            cur.execute(CREATE_METRICAS)
            cur.execute(
                "INSERT INTO metricas_validacao (mae_casa, mae_visitante, acuracia) VALUES (%s, %s, %s)",
                (mae_casa, mae_visitante, acuracia),
            )
        conn.commit()
        print("Tabela metricas_validacao gravada.")
    finally:
        conn.close()


def main() -> None:
    print("Lendo gold_atributos ...")
    df = read_gold()

    treino = df[df["data"] <  CORTE].copy()
    teste  = df[df["data"] >= CORTE].copy()
    print(f"Treino: {len(treino):,}  |  Teste: {len(teste):,}")

    print("Treinando modelos GLM Poisson ...")
    modelo_casa, modelo_visit = treinar(treino)

    mae_casa, mae_visitante, acuracia = validar(teste, modelo_casa, modelo_visit)
    print(f"\nMétricas de validação:")
    print(f"  MAE casa:       {mae_casa:.4f}")
    print(f"  MAE visitante:  {mae_visitante:.4f}")
    print(f"  Acurácia:       {acuracia:.4f}  ({acuracia*100:.1f}%)")

    salvar_modelos(modelo_casa, modelo_visit)
    gravar_metricas(mae_casa, mae_visitante, acuracia)


if __name__ == "__main__":
    main()
