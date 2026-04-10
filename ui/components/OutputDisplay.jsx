export default function OutputDisplay({ output }) {
  return (
    <section>
      <h2>Output</h2>
      <p>Proposed outlines and the final report should appear here.</p>
      <pre>{output || "No output yet."}</pre>
    </section>
  );
}