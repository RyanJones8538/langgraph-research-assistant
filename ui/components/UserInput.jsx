import { useState } from "react";

export default function UserInput({
  runPhase,
  onStartRun,
  onResumeRun,
  disabled = false,
}) {
  const [topic, setTopic] = useState("");
  const [revision, setRevision] = useState("");

  const isAwaitingReview = runPhase === "awaiting_review";

  const handleSubmit = (event) => {
    event.preventDefault();

    if (isAwaitingReview) {
      onResumeRun(revision);
      setRevision("");
      return;
    }

    onStartRun(topic);
    setTopic("");
  };

  return (
    <section>
      <h2>User Input</h2>
      <p>
        Submit a topic to start a new run. After an interrupt, submit revision
        feedback to resume.
      </p>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "0.75rem" }}>
          <label htmlFor="topic-input">Research topic</label>
          <textarea
            id="topic-input"
            rows={4}
            placeholder="Enter the research topic for the initial run"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            disabled={disabled || isAwaitingReview}
            style={{ display: "block", width: "100%" }}
          />
        </div>

        <div style={{ marginBottom: "0.75rem" }}>
          <label htmlFor="revision-input">Revision suggestions</label>
          <textarea
            id="revision-input"
            rows={4}
            placeholder="Enter outline feedback after an interrupt"
            value={revision}
            onChange={(event) => setRevision(event.target.value)}
            disabled={disabled || !isAwaitingReview}
            style={{ display: "block", width: "100%" }}
          />
        </div>

        <button
          type="submit"
          disabled={
            disabled ||
            (isAwaitingReview ? revision.trim().length === 0 : topic.trim().length === 0)
          }
        >
          {isAwaitingReview ? "Resume Interrupted Run" : "Start New Run"}
        </button>
      </form>
    </section>
  );
}