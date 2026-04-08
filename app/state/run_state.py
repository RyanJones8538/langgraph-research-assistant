import json

import psycopg

from app.config import DATABASE_URL


def _serialize_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return value


def update_run_state(request_id: str, **fields):
    if not request_id:
        raise RuntimeError("Missing request_id while updating run_state.")
    if not fields:
        return

    assignments = []
    values = []
    for key, value in fields.items():
        assignments.append(f"{key} = %s")
        values.append(_serialize_value(value))

    assignments.append("last_updated_at = NOW()")

    query = f"""
        UPDATE run_state
        SET {", ".join(assignments)}
        WHERE request_id = %s
    """
    values.append(request_id)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(query, tuple(values))
            if cur.rowcount != 1:
                raise RuntimeError(f"Failed to update run_state row for request_id={request_id}")
        conn.commit()