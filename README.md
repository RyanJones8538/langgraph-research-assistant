This is a LangGraph Research Assistant app. Run it by entering a user-input. The LLM will generate
a proposed outline for the final report. Either approve that outline or suggest revisions. Repeat this process until a desired outline is generated.

The app's structure contains a main graph with two subgraphs, the reader and writer. The reader subgraph generates questions about a given section,
uses Tavily to search for appropriate sources to answer those questions, evaluates those sources for appropriateness and credibility, and
checks for gaps in the required sources. If gaps are found, the app reroutes to source-gathering. This is repeated until there is sufficient coverage 
across all sections, or three iterations have been run, to prevent infinite loops.
The writer subgraph generates a proposed report and sends it to an editor, who evaluates the product for quality and appropriateness to the outline.
If any sections are found insufficient, they are sent back to the writer node. This process is repeated thrice at most, to prevent infinite loops.
 These exist because both contain domain-specific variables that
are useless elsewhere. A human-in-the-loop interrupt at the outlining phase allows the user more freedom to choose the final contents of the report.

To run, run the docker compose up --build in the langgraph-research-assistant folder. The app will appear on localhost:3000.

## Running unit tests

Install dependencies first:

```bash
python -m pip install -r requirements.txt
```

Then run tests with:

```bash
python -m pytest tests/unit -q
```

Note: On some systems (especially Windows/PowerShell), `pytest` may not be available as a standalone command even when installed. `python -m pytest ...` is the most portable way to run the test suite.


Tech Stack:
	LangGraph for agent coordination
	OpenAI gpt-4o-mini for the LLMs themselves
	React.js for the UI
	PostgreSQL to store data on runs
	Tavily to search for appropriate sources of information
	FastAPI to coordinate React.js with the backend

```mermaid
graph TD
    START([START]) --> init[initialize]
    init --> outline[generate_outline]
    outline --> review[request_outline_review]
    review --> parse[parse_review]

    parse -->|approve| condense[condense_topic]
    parse -->|revise| outline
    parse -->|cancel| END1([END])
    parse -->|invalid| inv[handle_invalid_review]
    inv --> END2([END])

    condense --> R

    subgraph R [Research Subgraph]
        r1([START]) --> r2[initialize_research]
        r2 -->|"× N sections"| r3[generate_questions_for_section]
        r3 -->|fan-in| r_sync1[sync_after_questions]
        r_sync1 -->|"× N incomplete"| r4[search_sources_by_section]
        r4 -->|fan-in| r_sync2[sync_after_search]
        r_sync2 -->|"× N sections"| r5[evaluate_sources_by_section]
        r5 -->|fan-in| r6{identify_gaps}
        r6 -->|complete| r7([END])
        r6 -->|"retry × N incomplete"| r4
    end

    R --> W

    subgraph W [Writer Subgraph]
        w1([START]) --> w2[initialize_writer]
        w2 -->|"× N sections"| w3[writer]
        w3 -->|fan-in| w_sync[sync_after_write]
        w_sync -->|"× N incomplete"| w4[editor]
        w4 -->|fan-in| w5{check_writer_complete}
        w5 -->|complete| w6([END])
        w5 -->|"retry × N incomplete"| w3
    end

    W --> END3([END])
```