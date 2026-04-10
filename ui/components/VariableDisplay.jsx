export default function VariableDisplay({ variables }) {
  return (
    <div className="variable-display">
      <h2>Current Variables:</h2>
      <pre>{JSON.stringify(variables, null, 2)}</pre>
    </div>
  );
}