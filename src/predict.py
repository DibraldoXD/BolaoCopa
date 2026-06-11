"""
Feature 07 — Previsão de partida + experimentos

Carrega modelos treinados, prevê os 72 jogos da Copa 2026 (→ previsoes) e
roda 4 experimentos de re-treino variando a meia-vida da recência (→ experimentos_mae).
"""

import datetime
import io
import pickle

import pandas as pd
import statsmodels.api as sm

from src.pg_conn import get_engine, get_raw_connection
from src.poisson import probabilidades_resultado
from src.train_model import CORTE, treinar, validar

DATA_REF = datetime.date(2026, 6, 11)

CONFIGS = {
    "sem_recencia": lambda a: 1.0,
    "meia_vida_3":  lambda a: 0.5 ** (a / 3),
    "meia_vida_5":  lambda a: 0.5 ** (a / 5),
    "meia_vida_10": lambda a: 0.5 ** (a / 10),
}

CREATE_PREVISOES = """
CREATE TABLE previsoes (
    id                       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    time_casa                TEXT,
    time_visitante           TEXT,
    gols_esperados_casa      DOUBLE PRECISION,
    gols_esperados_visitante DOUBLE PRECISION,
    prob_vitoria             DOUBLE PRECISION,
    prob_empate              DOUBLE PRECISION,
    prob_derrota             DOUBLE PRECISION
);
"""

CREATE_EXPERIMENTOS = """
CREATE TABLE experimentos_mae (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    config        TEXT,
    mae_casa      DOUBLE PRECISION,
    mae_visitante DOUBLE PRECISION
);
"""


def carregar_artefatos():
    modelo_casa  = pickle.load(open("models/modelo_poisson_casa.pkl",      "rb"))
    modelo_visit = pickle.load(open("models/modelo_poisson_visitante.pkl", "rb"))
    elo_df   = pd.read_sql("SELECT selecao, elo FROM silver_elo_atual", get_engine())
    elo_dict = dict(zip(elo_df["selecao"], elo_df["elo"]))
    return modelo_casa, modelo_visit, elo_dict


def prever_jogo(
    time_casa: str,
    time_visitante: str,
    neutro: bool,
    peso_torneio: int,
    elo_dict: dict,
    modelo_casa,
    modelo_visit,
) -> dict:
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
    lc = float(modelo_casa.predict(X).iloc[0])
    lv = float(modelo_visit.predict(X).iloc[0])
    pv, pe, pd_ = probabilidades_resultado(lc, lv)
    return {
        "gols_esperados_casa":      lc,
        "gols_esperados_visitante": lv,
        "prob_vitoria":  pv,
        "prob_empate":   pe,
        "prob_derrota":  pd_,
    }


def gerar_previsoes(modelo_casa, modelo_visit, elo_dict) -> pd.DataFrame:
    copa = pd.read_sql(
        "SELECT time_casa, time_visitante, neutro FROM silver_copa2026 ORDER BY data, id",
        get_engine(),
    )
    rows = []
    for row in copa.itertuples(index=False):
        p = prever_jogo(row.time_casa, row.time_visitante, row.neutro, 3,
                        elo_dict, modelo_casa, modelo_visit)
        rows.append({"time_casa": row.time_casa, "time_visitante": row.time_visitante, **p})
    return pd.DataFrame(rows)


def rodar_experimentos() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM gold_atributos ORDER BY data, jogo_id", get_engine())
    rows = []
    for config, fn in CONFIGS.items():
        df2 = df.copy()
        df2["peso_recencia"] = df2["data"].apply(lambda d: fn((DATA_REF - d).days / 365.25))
        treino2 = df2[df2["data"] <  CORTE].copy()
        teste2  = df2[df2["data"] >= CORTE].copy()
        m_c, m_v = treinar(treino2)
        mae_c, mae_v, _ = validar(teste2, m_c, m_v)
        rows.append({"config": config, "mae_casa": mae_c, "mae_visitante": mae_v})
        print(f"  {config}: MAE casa={mae_c:.4f}  visitante={mae_v:.4f}")
    return pd.DataFrame(rows)


def gravar_previsoes(df: pd.DataFrame, conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS previsoes;")
        cur.execute(CREATE_PREVISOES)
        buf = io.StringIO()
        df.to_csv(buf, index=False, na_rep="")
        buf.seek(0)
        cols = ", ".join(df.columns)
        cur.copy_expert(
            f"COPY previsoes ({cols}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')", buf
        )
    print(f"Tabela previsoes criada com {len(df)} linhas.")


def gravar_experimentos(df: pd.DataFrame, conn) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS experimentos_mae;")
        cur.execute(CREATE_EXPERIMENTOS)
        for row in df.itertuples(index=False):
            cur.execute(
                "INSERT INTO experimentos_mae (config, mae_casa, mae_visitante) VALUES (%s, %s, %s)",
                (row.config, row.mae_casa, row.mae_visitante),
            )
    print(f"Tabela experimentos_mae criada com {len(df)} linhas.")


def main() -> None:
    print("Carregando modelos e ELO ...")
    modelo_casa, modelo_visit, elo_dict = carregar_artefatos()

    print("Gerando previsões para os 72 jogos da Copa 2026 ...")
    df_prev = gerar_previsoes(modelo_casa, modelo_visit, elo_dict)
    print(df_prev[["time_casa","time_visitante","prob_vitoria","prob_empate","prob_derrota"]].head())

    print("\nRodando experimentos de recência ...")
    df_exp = rodar_experimentos()

    conn = get_raw_connection()
    try:
        gravar_previsoes(df_prev, conn)
        gravar_experimentos(df_exp, conn)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
