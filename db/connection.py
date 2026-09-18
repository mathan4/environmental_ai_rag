"""PostgreSQL + pgvector connection helper."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "eco_advisor")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_SSLMODE = os.getenv("POSTGRES_SSLMODE")


def get_connection():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn_kwargs = {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "cursor_factory": RealDictCursor,
        }
        if POSTGRES_SSLMODE:
            conn_kwargs["sslmode"] = POSTGRES_SSLMODE
        conn = psycopg2.connect(**conn_kwargs)
    try:
        register_vector(conn)
        conn.commit()
    except psycopg2.ProgrammingError:
        conn.rollback()
    return conn


def get_engine():
    if DATABASE_URL:
        db_url = DATABASE_URL
    else:
        ssl_part = f"?sslmode={POSTGRES_SSLMODE}" if POSTGRES_SSLMODE else ""
        db_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}{ssl_part}"
    return create_engine(db_url)


def init_schema() -> None:
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()
    conn = get_connection()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(schema)
    finally:
        conn.close()

