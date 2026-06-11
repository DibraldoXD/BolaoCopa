import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL não encontrado. Configure nos Streamlit Cloud Secrets."
        )
    return create_engine(url)


def get_raw_connection():
    return get_engine().raw_connection()
