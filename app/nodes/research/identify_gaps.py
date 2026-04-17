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
        research_iteration = state.get("research_iteration", 1)
        research_complete_by_section = state.get("research_complete_by_section", {})
        update_run_state(state.get("request_id", ), validated_sources=state.get("validated_sources", {}), last_completed_node="evaluate_sources", status="Evaluated quality of sources.")

        logger.info("Identifying gaps in research for iteration %d. Evaluated sources count: %d", research_iteration, len(evaluated_sources))

        research_done = True

        for section in evaluated_sources:
            if research_complete_by_section[section]:
                continue
            length = len(evaluated_sources[section].get("kept_sources", []))
            if length >= NUM_SOURCES_NEEDED_FOR_SECTION:
                research_complete_by_section[section] = True
                continue
            research_done = False
        if research_iteration >= NUM_RESEARCH_ITERATIONS:
            research_done = True

        # Only increment if another iteration will actually run — avoids showing one
        # run more than was executed when research completes naturally.
        if not research_done:
            research_iteration += 1

        research_sections_complete = sum(1 for v in research_complete_by_section.values() if v)

        logger.debug("Gaps identified for iteration %d. Research complete for sections: %s. Should research continue: %s", research_iteration, [section for section, complete in research_complete_by_section.items() if complete], research_done)

        update_run_state(state.get("request_id", ), research_iteration=research_iteration, research_done=research_done,
                         research_complete_by_section=research_complete_by_section, research_sections_complete=research_sections_complete,
                         last_completed_node="identify_gaps", status="Identified gaps in research sources.")
        return {
            "research_iteration": research_iteration,
            "research_done": research_done,
            "research_complete_by_section": research_complete_by_section,
            "research_sections_complete": research_sections_complete,
            "status": "Identified gaps in research sources."
        }
    return identify_gaps