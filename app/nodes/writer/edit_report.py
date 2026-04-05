def make_edit_report():
    def edit_report(state):
        number_of_iterations = state["writing_iteration"]
        number_of_iterations = number_of_iterations + 1
        should_continue = state["should_continue"]
        if number_of_iterations >= 3:
            should_continue = True
        return {
            "writing_iteration": number_of_iterations,
            "should_continue": should_continue,
        }
    return edit_report