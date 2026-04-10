import { useMemo, useState } from "react";
import { startRun, resumeRun } from "./api";
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
  streamingOutput: "",
  researchIteration: 0,
  writingIteration: 0,
  loading: false,
  error: "",
};

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
    }),
    [viewState]
  );

  const handleStartRun = async (topic) => {
    setViewState((previous) => ({
      ...previous,
      loading: true,
      error: "",
      runPhase: "running",
      status: "Starting run...",
      streamingOutput: "Calling /start_run...",
    }));

    try {
      const payload = await startRun(topic, viewState.threadId);

      setViewState((previous) => ({
        ...previous,
        loading: false,
        requestId: payload.request_id ?? previous.requestId,
        status: payload.status ?? "Run started.",
        output: payload.current_outline ?? payload.final_report ?? previous.output,
        streamingOutput: JSON.stringify(payload, null, 2),
        runPhase: payload.interrupted ? "awaiting_review" : "running",
      }));
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
      error: "",
      runPhase: "running",
      status: "Resuming interrupted run...",
      streamingOutput: "Calling /resume_run...",
    }));

    try {
      const payload = await resumeRun(viewState.threadId, feedback);

      setViewState((previous) => ({
        ...previous,
        loading: false,
        status: payload.status ?? "Run resumed.",
        output: payload.final_report ?? payload.current_outline ?? previous.output,
        streamingOutput: JSON.stringify(payload, null, 2),
        researchIteration:
          payload.research_iteration ?? previous.researchIteration,
        writingIteration: payload.writing_iteration ?? previous.writingIteration,
        runPhase: payload.completed ? "complete" : payload.interrupted ? "awaiting_review" : "running",
      }));
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
        Use <code>request_id</code> / <code>thread_id</code> for run identity and
        use <code>runPhase</code> only for UI flow. This avoids accidental resume
        calls when a boolean gets out of sync.
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
        <OutputDisplay output={viewState.output} />
        <StreamingDisplay
          mode={streamMode}
          status={viewState.status}
          streamText={viewState.streamingOutput}
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