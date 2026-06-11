import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def _get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        import streamlit as st
        url = st.secrets.get("DATABASE_URL")
        if url:
            os.environ["DATABASE_URL"] = url
            return url
    except Exception:
        pass
    raise KeyError("DATABASE_URL")


def get_engine():
    return create_engine(_get_url())


def get_raw_connection():
    return get_engine().raw_connection()
