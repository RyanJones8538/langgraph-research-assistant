from app.config import NUM_SOURCES_NEEDED_FOR_SECTION


def make_identify_gaps():
    def identify_gaps(state):
        evaluated_sources = state.get("validated_sources", {})
        number_of_runs = state.get("research_iteration", 0)
        research_complete = state.get("research_complete", {})
        should_continue = True

        for section in evaluated_sources:
            if research_complete[section]:
                continue
            if len(evaluated_sources[section].kept_sources) >= NUM_SOURCES_NEEDED_FOR_SECTION:
                research_complete[section] = True
                continue
            should_continue = False
        if number_of_runs > 3:
            should_continue = True
        return {
            "research_iteration": number_of_runs + 1,
            "should_continue": should_continue,
            "research_complete": research_complete
        }
    return identify_gaps