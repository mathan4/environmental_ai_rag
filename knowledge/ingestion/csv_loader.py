"""
Loads arbitrary CSV environmental datasets (e.g. regional soil surveys, species
occurrence records, climate normals) into their own PostgreSQL table, and registers them
in `dataset_registry` so they're discoverable without hardcoding column names anywhere.
"""
import os
import re
import pandas as pd
from db.connection import get_connection, get_engine


def _sanitize_table_name(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    return f"dataset_{name}"


def load_csv(path: str, conn=None) -> str:
    """Loads one CSV into its own PostgreSQL table. Returns the table name."""
    own_conn = conn is None
    conn = conn or get_connection()
    engine = get_engine()
    try:
        df = pd.read_csv(path)
        filename = os.path.basename(path)
        table_name = _sanitize_table_name(filename)

        df.to_sql(table_name, engine, if_exists="replace", index=False)

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO dataset_registry (dataset_name, source_file, columns, row_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(dataset_name) DO UPDATE SET
                    source_file=EXCLUDED.source_file, columns=EXCLUDED.columns,
                    row_count=EXCLUDED.row_count, loaded_at=CURRENT_TIMESTAMP
                """,
                (table_name, filename, ",".join(df.columns), len(df)),
            )
        conn.commit()
        print(f"  Loaded {filename} -> table '{table_name}' ({len(df)} rows, columns: {list(df.columns)})")
        return table_name
    finally:
        if own_conn:
            conn.close()


def load_all_csvs(directory: str) -> list[str]:
    """Loads every CSV in a directory. Returns the list of table names created."""
    if not os.path.isdir(directory):
        return []
    conn = get_connection()
    table_names = []
    try:
        for fname in os.listdir(directory):
            if not fname.lower().endswith(".csv"):
                continue
            try:
                table_names.append(load_csv(os.path.join(directory, fname), conn=conn))
            except Exception as e:
                print(f"  WARNING: failed to load {fname}: {e}")
    finally:
        conn.close()
    return table_names


def list_datasets() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM dataset_registry")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def query_dataset(table_name: str, filters: dict = None, limit: int = 20) -> list[dict]:
    """
    Generic filtered query against a loaded dataset table.
    filters: {column_name: value} — exact match, ANDed together.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT columns FROM dataset_registry WHERE dataset_name = %s", (table_name,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Unknown dataset table: {table_name}")
            valid_columns = set(row["columns"].split(","))

            where_clauses, params = [], []
            for col, val in (filters or {}).items():
                if col not in valid_columns:
                    raise ValueError(f"'{col}' is not a column in dataset '{table_name}'")
                where_clauses.append(f'"{col}" = %s')
                params.append(val)

            query = f'SELECT * FROM "{table_name}"'
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            query += " LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

