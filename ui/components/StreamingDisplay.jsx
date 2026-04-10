export default function StreamingDisplay({ output }) {
  return (
    <div className="streaming-display">
      <h2>Streaming Output:</h2>
      <pre>{output}</pre>
    </div>
  );
}