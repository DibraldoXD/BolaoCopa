"""
Feature 05 — Atributos Gold: tabela de treino

Lê silver_ponderado JOIN silver_elo_pre_jogo (apenas jogos competitivos),
deriva dif_elo, valida nulos e grava gold_atributos via COPY (idempotente).
"""

import io

import pandas as pd

from src.pg_conn import get_engine, get_raw_connection

QUERY = """
SELECT
    s.id              AS jogo_id,
    s.data,
    s.time_casa,
    s.time_visitante,
    e.elo_casa,
    e.elo_visitante,
    s.neutro,
    s.peso_torneio,
    s.peso_recencia,
    s.gols_casa,
    s.gols_visitante
FROM silver_ponderado s
JOIN silver_elo_pre_jogo e ON e.jogo_id = s.id
WHERE NOT s.eh_amistoso
ORDER BY s.data, s.id
"""

ATRIBUTOS = [
    "elo_casa", "elo_visitante", "dif_elo", "neutro",
    "peso_torneio", "peso_recencia", "gols_casa", "gols_visitante",
]

CREATE_SQL = """
CREATE TABLE gold_atributos (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jogo_id         BIGINT,
    data            DATE,
    time_casa       TEXT,
    time_visitante  TEXT,
    elo_casa        DOUBLE PRECISION,
    elo_visitante   DOUBLE PRECISION,
    dif_elo         DOUBLE PRECISION,
    neutro          BOOLEAN,
    peso_torneio    INTEGER,
    peso_recencia   DOUBLE PRECISION,
    gols_casa       INTEGER,
    gols_visitante  INTEGER
);
"""


def build_gold() -> pd.DataFrame:
    df = pd.read_sql(QUERY, get_engine())
    df["gols_casa"] = df["gols_casa"].astype("Int64")
    df["gols_visitante"] = df["gols_visitante"].astype("Int64")

    df["dif_elo"] = df["elo_casa"] - df["elo_visitante"]

    assert df[ATRIBUTOS].isnull().sum().sum() == 0, "Nulos encontrados nos atributos!"

    return df[["jogo_id", "data", "time_casa", "time_visitante"] + ATRIBUTOS]


def print_inventory(df: pd.DataFrame) -> None:
    print(f"\n{'='*50}")
    print(f"gold_atributos — Linhas: {len(df):,}")
    print("\nEstatísticas dos atributos numéricos:")
    cols = ["elo_casa", "elo_visitante", "dif_elo", "peso_recencia"]
    print(df[cols].describe().round(2).to_string())
    print("=" * 50)


def load_to_db(df: pd.DataFrame) -> None:
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS gold_atributos;")
            cur.execute(CREATE_SQL)

            buf = io.StringIO()
            df.to_csv(buf, index=False, na_rep="")
            buf.seek(0)

            cols = ", ".join(df.columns)
            cur.copy_expert(
                f"COPY gold_atributos ({cols}) FROM STDIN "
                f"WITH (FORMAT CSV, HEADER TRUE, NULL '')",
                buf,
            )
        conn.commit()
        print(f"\nTabela gold_atributos criada com {len(df):,} linhas.")
    finally:
        conn.close()


def main() -> None:
    print("Construindo gold_atributos ...")
    df = build_gold()
    print_inventory(df)
    load_to_db(df)


if __name__ == "__main__":
    main()
