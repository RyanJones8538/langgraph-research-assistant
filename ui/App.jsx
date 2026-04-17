import { useMemo, useState } from "react";
import { streamStartRun, streamResumeRun } from "./api";
import OutputDisplay from "./components/OutputDisplay";
import StreamingDisplay from "./components/StreamingDisplay";
import UserInput from "./components/UserInput";
import VariableDisplay from "./components/VariableDisplay";

const initialViewState = {
  runPhase: "idle", // idle -> running -> awaiting_review -> running -> complete
  threadId: `thread-${crypto.randomUUID()}`,
  requestId: "",
  status: "Waiting for input.",
  output: "",
  tokenChunks: [],  // [{node, content}] — one entry per node, grouped in order
  streamingOutput: "",
  researchIteration: 0,
  writingIteration: 0,
  totalSections: 0,
  researchSectionsComplete: 0,
  writingSectionsComplete: 0,
  statusHistory: [],
  loading: false,
  error: "",
};

function hasGraphInterrupt(payload) {
  const statusText = String(payload?.status ?? "").toLowerCase();
  const awaitingReviewFromStatus =
    statusText.includes("awaiting review") || statusText.includes("reviewing user comment");
  const hasOutlineWithoutFinalReport = Boolean(payload?.current_outline && !payload?.final_report);

  return Boolean(
    payload?.interrupted ||
      payload?.interrupt ||
      payload?.__interrupt__ ||
      awaitingReviewFromStatus ||
      hasOutlineWithoutFinalReport
  );
}

function hasCompletedRun(payload) {
  return Boolean(payload?.completed || payload?.final_report);
}

function appendTokenChunk(chunks, node, content) {
  const last = chunks.at(-1);
  if (last && last.node === node) {
    return [...chunks.slice(0, -1), { node, content: last.content + content }];
  }
  return [...chunks, { node, content }];
}

export default function App() {
  const [viewState, setViewState] = useState(initialViewState);
  const [streamMode, setStreamMode] = useState("basic");

  const variables = useMemo(
    () => ({
      run_phase: viewState.runPhase,
      thread_id: viewState.threadId,
      request_id: viewState.requestId,
      status: viewState.status,
      research_iteration: viewState.researchIteration,
      writing_iteration: viewState.writingIteration,
      research_sections_complete: viewState.totalSections > 0
        ? `${viewState.researchSectionsComplete} / ${viewState.totalSections}`
        : null,
      writing_sections_complete: viewState.totalSections > 0
        ? `${viewState.writingSectionsComplete} / ${viewState.totalSections}`
        : null,
      status_history: viewState.statusHistory,
    }),
    [viewState]
  );

  const handleStartRun = async (topic) => {
    const nextThreadId = `thread-${crypto.randomUUID()}`;
    setViewState((previous) => ({
      ...previous,
      threadId: nextThreadId,
      requestId: "",
      output: "",
      tokenChunks: [],
      statusHistory: [],
      loading: true,
      error: "",
      runPhase: "running",
      status: "Starting run...",
      streamingOutput: "Starting run...",
    }));

    try {
      for await (const event of streamStartRun(topic, nextThreadId)) {
        if (event.type === "status_update") {
          setViewState((previous) => ({
            ...previous,
            status: event.status,
            statusHistory: [...previous.statusHistory, event.status],
          }));
        } else if (event.type === "token") {
          setViewState((previous) => ({
            ...previous,
            tokenChunks: appendTokenChunk(previous.tokenChunks, event.node, event.content),
          }));
        } else if (event.type === "variables_update") {
          setViewState((previous) => ({
            ...previous,
            researchIteration: event.research_iteration ?? previous.researchIteration,
            writingIteration: event.writing_iteration ?? previous.writingIteration,
            totalSections: event.total_sections ?? previous.totalSections,
            researchSectionsComplete: event.research_sections_complete ?? previous.researchSectionsComplete,
            writingSectionsComplete: event.writing_sections_complete ?? previous.writingSectionsComplete,
          }));
        } else if (event.type === "result") {
          setViewState((previous) => ({
            ...previous,
            loading: false,
            requestId: event.request_id ?? previous.requestId,
            status: event.status ?? "Run started.",
            statusHistory: event.status_history ?? previous.statusHistory,
            output: event.current_outline || event.final_report || previous.output,
            streamingOutput: JSON.stringify(event, null, 2),
            researchIteration: event.research_iteration ?? previous.researchIteration,
            writingIteration: event.writing_iteration ?? previous.writingIteration,
            totalSections: event.total_sections ?? previous.totalSections,
            researchSectionsComplete: event.research_sections_complete ?? previous.researchSectionsComplete,
            writingSectionsComplete: event.writing_sections_complete ?? previous.writingSectionsComplete,
            runPhase: hasGraphInterrupt(event)
              ? "awaiting_review"
              : hasCompletedRun(event)
                ? "complete"
                : "running",
          }));
        } else if (event.type === "error") {
          setViewState((previous) => ({
            ...previous,
            loading: false,
            error: event.message,
            status: "Run failed.",
            runPhase: "idle",
          }));
        }
      }
    } catch (error) {
      setViewState((previous) => ({
        ...previous,
        loading: false,
        error: error.message,
        status: "Start run failed.",
        runPhase: "idle",
      }));
    }
  };

  const handleResumeRun = async (feedback) => {
    setViewState((previous) => ({
      ...previous,
      loading: true,
      tokenChunks: [],
      error: "",
      runPhase: "running",
      status: "Resuming interrupted run...",
      streamingOutput: "Streaming /stream_resume...",
    }));

    try {
      for await (const event of streamResumeRun(viewState.threadId, feedback)) {
        if (event.type === "status_update") {
          setViewState((previous) => ({
            ...previous,
            status: event.status,
            statusHistory: [...previous.statusHistory, event.status],
          }));
        } else if (event.type === "token") {
          setViewState((previous) => ({
            ...previous,
            tokenChunks: appendTokenChunk(previous.tokenChunks, event.node, event.content),
          }));
        } else if (event.type === "variables_update") {
          setViewState((previous) => ({
            ...previous,
            researchIteration: event.research_iteration ?? previous.researchIteration,
            writingIteration: event.writing_iteration ?? previous.writingIteration,
            totalSections: event.total_sections ?? previous.totalSections,
            researchSectionsComplete: event.research_sections_complete ?? previous.researchSectionsComplete,
            writingSectionsComplete: event.writing_sections_complete ?? previous.writingSectionsComplete,
          }));
        } else if (event.type === "result") {
          setViewState((previous) => ({
            ...previous,
            loading: false,
            status: event.status ?? "Run resumed.",
            statusHistory: event.status_history ?? previous.statusHistory,
            output: event.final_report || event.current_outline || previous.output,
            streamingOutput: JSON.stringify(event, null, 2),
            researchIteration: event.research_iteration ?? previous.researchIteration,
            writingIteration: event.writing_iteration ?? previous.writingIteration,
            totalSections: event.total_sections ?? previous.totalSections,
            researchSectionsComplete: event.research_sections_complete ?? previous.researchSectionsComplete,
            writingSectionsComplete: event.writing_sections_complete ?? previous.writingSectionsComplete,
            runPhase: hasCompletedRun(event)
              ? "complete"
              : hasGraphInterrupt(event)
                ? "awaiting_review"
                : "running",
          }));
        } else if (event.type === "error") {
          setViewState((previous) => ({
            ...previous,
            loading: false,
            error: event.message,
            status: "Run failed.",
            runPhase: "awaiting_review",
          }));
        }
      }
    } catch (error) {
      setViewState((previous) => ({
        ...previous,
        loading: false,
        error: error.message,
        status: "Resume run failed.",
        runPhase: "awaiting_review",
      }));
    }
  };

  return (
    <div style={{ padding: "1.5rem", fontFamily: "sans-serif" }}>
      <h1>LangGraph Research Assistant</h1>
      <p>
        A proposed outline and eventual final report are displayed here.
      </p>

      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="stream-mode">Streaming mode: </label>
        <select
          id="stream-mode"
          value={streamMode}
          onChange={(event) => setStreamMode(event.target.value)}
        >
          <option value="basic">Basic (status)</option>
          <option value="verbose">Verbose (raw stream)</option>
          <option value="tokens">Token stream (LLM output)</option>
        </select>
      </div>

      {viewState.error ? (
        <p style={{ color: "crimson" }}>
          <strong>Error:</strong> {viewState.error}
        </p>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "1rem",
          alignItems: "start",
        }}
      >
        <OutputDisplay
          output={viewState.output}
          statusHistory={viewState.statusHistory}
          runPhase={viewState.runPhase}
        />
        <StreamingDisplay
          mode={streamMode}
          status={viewState.status}
          streamText={viewState.streamingOutput}
          tokenChunks={viewState.tokenChunks}
        />
        <UserInput
          runPhase={viewState.runPhase}
          onStartRun={handleStartRun}
          onResumeRun={handleResumeRun}
          disabled={viewState.loading}
        />
        <VariableDisplay variables={variables} />
      </div>
    </div>
  );
}
