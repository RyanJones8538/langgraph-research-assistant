import json

import psycopg

from app.config import DATABASE_URL
from psycopg import Connection
from psycopg import sql
from psycopg.sql import Composable


def _serialize_value(value):
    """
    Serializes a value for storage in Postgres. If the value is a dictionary or list, it converts it to a JSON string. Otherwise, it returns the value as is.
    Args:
        value: The value to serialize.
    Returns:
        The serialized value.
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value

def _connect_with_host_fallback() -> Connection:
    """
    Attempts to connect to the Postgres database using the DATABASE_URL. 
    If it encounters an OperationalError that indicates a failure to resolve the host (which can happen in certain environments like Docker),
      it modifies the DATABASE_URL to replace the host with "localhost" and tries to connect again. 
      This provides a fallback mechanism for connecting to the database in different deployment scenarios.
    Returns:
        Connection to PostgresSQL database.
    """
    try:
        return psycopg.connect(DATABASE_URL)
    except psycopg.OperationalError as exc:
        err_text = str(exc).lower()
        if "failed to resolve host 'db'" not in err_text and "getaddrinfo failed" not in err_text:
            raise
        fallback_url = DATABASE_URL.replace("@db:", "@localhost:")
        return psycopg.connect(fallback_url)
    
def update_run_state(request_id: str, **fields):
    """
    Updates the run state in Postgres for a given request_id with the provided fields. 
    It first attempts to update the existing row for the request_id, and if no rows are updated (which could happen if the initialize row was missing), 
    it performs an upsert to create or update the row as needed.
    Args:
        request_id: The unique identifier for the run, used to locate the correct row in the run_state table.
        **fields: Arbitrary keyword arguments representing the fields to update in the run_state. 
        The keys should correspond to column names in the run_state table, and the values will be serialized and stored in those columns.
    """
    if not request_id:
        raise RuntimeError("Missing request_id while updating run_state.")
    if not fields:
        return

    serialized_fields = {key: _serialize_value(value) for key, value in fields.items()}
    field_names = list(serialized_fields.keys())

    with _connect_with_host_fallback() as conn:
        with conn.cursor() as cur:
            set_fragments: list[Composable] = [
                sql.SQL("{} = %s").format(sql.Identifier(field_name))
                for field_name in field_names
            ]
            set_fragments.append(sql.SQL("last_updated_at = NOW()"))

            update_query = sql.SQL("UPDATE run_state SET {} WHERE request_id = %s").format(
                sql.SQL(", ").join(set_fragments)
            )
            update_values = [serialized_fields[field_name] for field_name in field_names]
            cur.execute(update_query, (*update_values, request_id))

    # If initialize row was missing for any reason, recover with an upsert
            if cur.rowcount == 0:
                insert_columns = [sql.Identifier("request_id"), *[sql.Identifier(name) for name in field_names]]
                insert_values = [request_id, *[serialized_fields[field_name] for field_name in field_names]]

                upsert_assignments: list[Composable] = [
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(name), sql.Identifier(name))
                    for name in field_names
                ]
                upsert_assignments.append(sql.SQL("last_updated_at = NOW()"))

                upsert_query = sql.SQL(
                    """
                    INSERT INTO run_state ({columns}, created_at, last_updated_at)
                    VALUES ({values}, NOW(), NOW())
                    ON CONFLICT (request_id) DO UPDATE
                    SET {updates}
                    """
                ).format(
                    columns=sql.SQL(", ").join(insert_columns),
                    values=sql.SQL(", ").join(sql.SQL("%s") for _ in insert_values),
                    updates=sql.SQL(", ").join(upsert_assignments),
                )

                cur.execute(upsert_query, tuple(insert_values))
        conn.commit()