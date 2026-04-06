from dotenv import load_dotenv
import psycopg

from app.config import DATABASE_URL
from app.graph.builder import build_graph, OutlineState
from uuid import uuid4

from app.models.classes import OutlineContent

load_dotenv()

graph = build_graph()

def run(topic: str):
    initial_state: OutlineState = {
        "request_id": str(uuid4()),
        "topic": topic,
        "request_messages": [topic],
        "current_outline": "",
        "section_questions": {},
        "outline_object": OutlineContent(outline_formatted=[]),
        "outline_history": [],
        "review_action": None,
        "review_comment": None,
        "validated_sources": {},
        "status": "Initializing Research Assistant",
    }
    create_run_sql(initial_state["request_id"], topic)
    return graph.invoke(initial_state)

if __name__ == "__main__":
    result = run("Causes of World War I")
    print(result)

def create_run_sql(request_id, topic):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO run_state (request_id, topic, status, created_at, last_updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                 ON CONFLICT (request_id) DO UPDATE 
                 SET topic = EXCLUDED.topic,
                     status = EXCLUDED.status,
                     last_updated_at = NOW()
                 WHERE run_state.request_id = EXCLUDED.request_id
                """,
                (
                    request_id,
                    topic,
                    "Initializing Research Assistant",
                ),
            )
        conn.commit()