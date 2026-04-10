export default function StreamingDisplay({ mode, status, streamText }) {
  return (
    <section>
      <h2>Streaming State</h2>
      <p>
        <strong>Mode:</strong> {mode === "verbose" ? "Verbose" : "Basic"}
      </p>
      {mode === "verbose" ? (
        <pre>{streamText || "No token stream received yet."}</pre>
      ) : (
        <pre>{status || "No status update yet."}</pre>
      )}
    </section>
  );
}