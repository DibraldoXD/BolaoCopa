"""
Feature 04 — ELO: força das seleções

Lê silver_ponderado em ordem cronológica, calcula ELO pré-jogo de cada partida
e grava silver_elo_pre_jogo (anti-leakage) e silver_elo_atual via COPY (idempotente).
"""

import io
from collections import defaultdict

import pandas as pd

from src.pg_conn import get_engine, get_raw_connection

ELO_INICIAL = 1500
HFA = 100
K_POR_NIVEL = {1: 20, 2: 40, 3: 60}

CREATE_PRE_JOGO = """
CREATE TABLE silver_elo_pre_jogo (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jogo_id         BIGINT,
    data            DATE,
    time_casa       TEXT,
    time_visitante  TEXT,
    elo_casa        DOUBLE PRECISION,
    elo_visitante   DOUBLE PRECISION
);
"""

CREATE_ATUAL = """
CREATE TABLE silver_elo_atual (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    selecao         TEXT,
    elo             DOUBLE PRECISION
);
"""


def read_silver_ponderado() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT id, data, time_casa, time_visitante, "
        "gols_casa, gols_visitante, neutro, peso_torneio "
        "FROM silver_ponderado ORDER BY data, id",
        get_engine(),
    )


def compute_elo(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    elo: dict[str, float] = defaultdict(lambda: ELO_INICIAL)
    pre_jogo_rows = []

    for row in df.itertuples(index=False):
        ec = elo[row.time_casa]
        ev = elo[row.time_visitante]

        hfa = 0 if row.neutro else HFA
        E_c = 1 / (1 + 10 ** ((ev - ec - hfa) / 400))
        E_v = 1 - E_c

        if row.gols_casa > row.gols_visitante:
            S_c = 1.0
        elif row.gols_casa == row.gols_visitante:
            S_c = 0.5
        else:
            S_c = 0.0

        pre_jogo_rows.append((row.id, row.data, row.time_casa, row.time_visitante, ec, ev))

        K = K_POR_NIVEL[row.peso_torneio]
        elo[row.time_casa] += K * (S_c - E_c)
        elo[row.time_visitante] += K * ((1 - S_c) - E_v)

    df_pre = pd.DataFrame(
        pre_jogo_rows,
        columns=["jogo_id", "data", "time_casa", "time_visitante", "elo_casa", "elo_visitante"],
    )

    df_atual = (
        pd.DataFrame(list(elo.items()), columns=["selecao", "elo"])
        .sort_values("elo", ascending=False)
        .reset_index(drop=True)
    )

    return df_pre, df_atual


def print_inventory(df_pre: pd.DataFrame, df_atual: pd.DataFrame) -> None:
    print(f"\n{'='*50}")
    print(f"silver_elo_pre_jogo — Linhas: {len(df_pre):,}")
    print(f"silver_elo_atual    — Seleções: {len(df_atual):,}")
    print("\nTop 10 ELO atual:")
    print(df_atual.head(10).to_string(index=False))
    print("=" * 50)


def load_table(df: pd.DataFrame, table: str, create_sql: str, conn) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {table};")
        cur.execute(create_sql)

        buf = io.StringIO()
        df.to_csv(buf, index=False, na_rep="")
        buf.seek(0)

        cols = ", ".join(df.columns)
        cur.copy_expert(
            f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')",
            buf,
        )
    print(f"Tabela {table} criada com {len(df):,} linhas.")


def main() -> None:
    print("Lendo silver_ponderado ...")
    df = read_silver_ponderado()
    print(f"Ponderado: {len(df):,} linhas.")

    df_pre, df_atual = compute_elo(df)
    print_inventory(df_pre, df_atual)

    conn = get_raw_connection()
    try:
        load_table(df_pre, "silver_elo_pre_jogo", CREATE_PRE_JOGO, conn)
        load_table(df_atual, "silver_elo_atual", CREATE_ATUAL, conn)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
