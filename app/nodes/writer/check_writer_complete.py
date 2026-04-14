from app.config import NUM_WRITING_ITERATIONS


def generate_check_writer_complete():
    def check_writer_complete(state):
        writing_complete = state.get("writing_complete", {})
        outline_object = state.get("outline_object", {})
        writing_iteration = state.get("writing_iteration", 0)

        if (writing_iteration >= NUM_WRITING_ITERATIONS):
            return {"should_writer_continue": True}

        for section_title in outline_object.keys():
            if writing_complete.get(section_title) != True:
                return {"should_writer_continue": False}
        return {"should_writer_continue": True}
    return check_writer_complete

