import json
import psycopg

from app.config import DATABASE_URL, NUM_RESEARCH_ITERATIONS, NUM_SOURCES_NEEDED_FOR_SECTION


def make_identify_gaps():
    def identify_gaps(state):
        evaluated_sources = state.get("validated_sources", {})
        number_of_runs = state.get("research_iteration", 0)
        research_complete = state.get("research_complete", {})
        should_continue = True
        number_of_runs+=1

        for section in evaluated_sources:
            if research_complete[section]:
                continue
            if len(evaluated_sources[section].kept_sources) >= NUM_SOURCES_NEEDED_FOR_SECTION:
                research_complete[section] = True
                continue
            should_continue = False
        if number_of_runs >= NUM_RESEARCH_ITERATIONS:
            should_continue = True
        update_sql_identify_gaps(number_of_runs, should_continue, research_complete, state.get("request_id", ""))
        return {
            "research_iteration": number_of_runs,
            "should_research_continue": should_continue,
            "research_complete": research_complete
        }
    return identify_gaps

def update_sql_identify_gaps(research_iteration, should_research_continue, research_complete, request_id):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE run_state
                SET 
                    research_iteration = %s,
                    should_research_continue = %s,
                    research_complete = %s,
                    last_completed_node = %s,
                    status = %s,
                    last_updated_at = NOW()
                WHERE request_id = %s
                """,
                (
                    research_iteration,
                    should_research_continue,
                    json.dumps(research_complete),
                    "identify_gaps",
                    "Searched for gaps in research sources.",
                    request_id,
                ),
            )