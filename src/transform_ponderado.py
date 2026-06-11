"""
Feature 03 — Pesos: torneio + recência

Lê silver_jogos, deriva peso_torneio (1/2/3) e peso_recencia (decaimento
exponencial, meia-vida 5 anos) e grava silver_ponderado via COPY (idempotente).
"""

import datetime
import io

import pandas as pd

from src.pg_conn import get_engine, get_raw_connection

DATA_REF = datetime.date(2026, 6, 11)

NIVEL3 = {"FIFA World Cup", "Confederations Cup", "CONMEBOL–UEFA Cup of Champions"}
CONTINENTAIS = {
    "UEFA Euro",
    "Copa América",
    "African Cup of Nations",
    "AFC Asian Cup",
    "Gold Cup",
    "Oceania Nations Cup",
}

CREATE_SQL = """
CREATE TABLE silver_ponderado (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    data            DATE,
    time_casa       TEXT,
    time_visitante  TEXT,
    gols_casa       INTEGER,
    gols_visitante  INTEGER,
    torneio         TEXT,
    cidade          TEXT,
    pais            TEXT,
    neutro          BOOLEAN,
    eh_amistoso     BOOLEAN,
    peso_torneio    INTEGER,
    peso_recencia   DOUBLE PRECISION
);
"""


def read_silver() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM silver_jogos ORDER BY id", get_engine())
    df = df.drop(columns=["id"])
    df["gols_casa"] = df["gols_casa"].astype("Int64")
    df["gols_visitante"] = df["gols_visitante"].astype("Int64")
    return df


def classificar(torneio: str) -> int:
    if torneio in NIVEL3:
        return 3
    t = torneio.lower()
    if "qualification" in t or "nations league" in t or torneio in CONTINENTAIS:
        return 2
    return 1


def add_peso_torneio(df: pd.DataFrame) -> pd.DataFrame:
    df["peso_torneio"] = df["torneio"].map(classificar).astype(int)
    return df


def add_peso_recencia(df: pd.DataFrame) -> pd.DataFrame:
    df["idade_anos"] = df["data"].apply(lambda d: (DATA_REF - d).days / 365.25)
    df["peso_recencia"] = 0.5 ** (df["idade_anos"] / 5)
    df = df.drop(columns=["idade_anos"])
    return df


def print_inventory(df: pd.DataFrame) -> None:
    print(f"\n{'='*50}")
    print(f"silver_ponderado — Linhas: {len(df):,}")
    print("\nDistribuição peso_torneio:")
    print(df["peso_torneio"].value_counts().sort_index().to_string())
    print(f"\npeso_recencia — min: {df['peso_recencia'].min():.6f}  max: {df['peso_recencia'].max():.6f}")
    print("=" * 50)


def load_to_db(df: pd.DataFrame) -> None:
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS silver_ponderado;")
            cur.execute(CREATE_SQL)

            buf = io.StringIO()
            df.to_csv(buf, index=False, na_rep="")
            buf.seek(0)

            cols = ", ".join(df.columns)
            cur.copy_expert(
                f"COPY silver_ponderado ({cols}) FROM STDIN "
                f"WITH (FORMAT CSV, HEADER TRUE, NULL '')",
                buf,
            )
        conn.commit()
        print(f"\nTabela silver_ponderado criada com {len(df):,} linhas.")
    finally:
        conn.close()


def main() -> None:
    print("Lendo silver_jogos ...")
    df = read_silver()
    print(f"Silver: {len(df):,} linhas.")

    df = add_peso_torneio(df)
    df = add_peso_recencia(df)

    print_inventory(df)
    load_to_db(df)


if __name__ == "__main__":
    main()
