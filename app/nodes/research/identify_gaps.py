import json
import psycopg

from app.config import DATABASE_URL, NUM_RESEARCH_ITERATIONS, NUM_SOURCES_NEEDED_FOR_SECTION
from app.state.run_state import update_run_state


def make_identify_gaps():
    def identify_gaps(state):
        evaluated_sources = state.get("validated_sources", {})
        number_of_research_runs = state.get("research_iteration", 0)
        research_complete = state.get("research_complete", {})
        should_research_continue = True
        number_of_research_runs+=1

        for section in evaluated_sources:
            if research_complete[section]:
                continue
            if len(evaluated_sources[section].get("kept_sources", [])) >= NUM_SOURCES_NEEDED_FOR_SECTION:
                research_complete[section] = True
                continue
            should_research_continue = False
        if number_of_research_runs >= NUM_RESEARCH_ITERATIONS:
            should_research_continue = True
        update_run_state(state.get("request_id", ), research_iteration=number_of_research_runs, should_research_continue=should_research_continue, research_complete=research_complete, last_completed_node="identify_gaps", status="Identifying gaps in research sources.")
        return {
            "research_iteration": number_of_research_runs,
            "should_research_continue": should_research_continue,
            "research_complete": research_complete
        }
    return identify_gaps