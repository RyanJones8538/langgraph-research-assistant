import logging

from app.config import NUM_RESEARCH_ITERATIONS, NUM_SOURCES_NEEDED_FOR_SECTION
from app.state.run_state import update_run_state

logger = logging.getLogger(__name__)

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
        research_complete_by_section = state.get("research_complete_by_section", {})
        update_run_state(state.get("request_id", ), validated_sources=state.get("validated_sources", {}), last_completed_node="evaluate_sources", status="Evaluated quality of sources.")
        
        logger.info("Identifying gaps in research for iteration %d. Evaluated sources count: %d", number_of_research_runs, len(evaluated_sources))
        
        research_done = True
        number_of_research_runs+=1

        for section in evaluated_sources:
            if research_complete_by_section[section]:
                continue
            length = len(evaluated_sources[section].get("kept_sources", []))
            if length >= NUM_SOURCES_NEEDED_FOR_SECTION:
                research_complete_by_section[section] = True
                continue
            research_done = False
        if number_of_research_runs >= NUM_RESEARCH_ITERATIONS:
            research_done = True

        logger.debug("Gaps identified for iteration %d. Research complete for sections: %s. Should research continue: %s", number_of_research_runs, [section for section, complete in research_complete_by_section.items() if complete], research_done)
        
        update_run_state(state.get("request_id", ), research_iteration=number_of_research_runs, research_done=research_done, 
                         research_complete_by_section=research_complete_by_section, last_completed_node="identify_gaps", status="Identified gaps in research sources.")
        return {
            "research_iteration": number_of_research_runs,
            "research_done": research_done,
            "research_complete_by_section": research_complete_by_section,
            "status": "Identified gaps in research sources."
        }
    return identify_gaps