function FieldValue({ value }) {
  if (value === null || value === undefined) {
    return <span style={{ color: "#888" }}>—</span>;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span style={{ color: "#888" }}>[]</span>;
    return (
      <ul style={{ margin: "0.2rem 0 0 1.25rem", padding: 0 }}>
        {value.map((item, i) => (
          <li key={i} style={{ fontSize: "0.9rem" }}>{String(item)}</li>
        ))}
      </ul>
    );
  }
  if (typeof value === "string" && value.includes("\n")) {
    return (
      <pre style={{ margin: "0.2rem 0 0 0", fontSize: "0.9rem", whiteSpace: "pre-wrap" }}>
        {value}
      </pre>
    );
  }
  return <span style={{ fontSize: "0.9rem" }}>{String(value)}</span>;
}

export default function VariableDisplay({ variables }) {
  return (
    <section>
      <h2>Graph State</h2>
      <p>Track request identity and iteration counters from graph state.</p>
      {Object.entries(variables).map(([key, value]) => (
        <div key={key} style={{ marginBottom: "0.6rem" }}>
          <strong>{key}</strong>
          <div style={{ marginLeft: "0.75rem" }}>
            <FieldValue value={value} />
          </div>
        </div>
      ))}
    </section>
  );
}
