import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def get_engine():
    url = os.environ["DATABASE_URL"]
    return create_engine(url)


def get_raw_connection():
    return get_engine().raw_connection()
