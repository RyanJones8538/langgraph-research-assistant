from app.config import NUM_RESEARCH_ITERATIONS, NUM_SOURCES_NEEDED_FOR_SECTION
from app.state.run_state import update_run_state


def make_identify_gaps():
    """
    Wrapper function to create identify_gaps node for research graph. 
    This node analyzes the evaluated sources for each section and determines if there are any gaps in the research that need to be filled by another iteration of searching for sources. 
    It updates the run state with the current iteration of research, whether research should continue, and which sections are complete.
    Returns:
        identify_gaps function, which can be used as a node in the research graph.
    """
    def identify_gaps(state):
        """
        Identify gaps in the research based on the evaluated sources and update the run state accordingly.
        Args:
            state: The current state of the graph.
        Returns:
            Iteration of research, whether research should continue, and which sections are complete.
        """
        evaluated_sources = state.get("validated_sources", {})
        number_of_research_runs = state.get("research_iteration", 0)
        research_complete = state.get("research_complete", {})
        update_run_state(state.get("request_id", ), validated_sources=state.get("validated_sources", {}), last_completed_node="evaluate_sources", status="Evaluated quality of sources.")
        
        should_research_continue = True
        number_of_research_runs+=1

        for section in evaluated_sources:
            if research_complete[section]:
                continue
            length = len(evaluated_sources[section].get("kept_sources", []))
            if length >= NUM_SOURCES_NEEDED_FOR_SECTION:
                research_complete[section] = True
                continue
            should_research_continue = False
        if number_of_research_runs >= NUM_RESEARCH_ITERATIONS:
            should_research_continue = True
        update_run_state(state.get("request_id", ), research_iteration=number_of_research_runs, should_research_continue=should_research_continue, 
                         research_complete=research_complete, last_completed_node="identify_gaps", status="Identified gaps in research sources.")
        return {
            "research_iteration": number_of_research_runs,
            "should_research_continue": should_research_continue,
            "research_complete": research_complete,
            "status": "Identified gaps in research sources."
        }
    return identify_gaps