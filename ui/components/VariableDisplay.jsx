export default function VariableDisplay({ variables }) {
  return (
    <section>
      <h2>Graph State</h2>
      <p>Track request identity and iteration counters from graph state.</p>
      <pre>{JSON.stringify(variables, null, 2)}</pre>
    </section>
  );
}