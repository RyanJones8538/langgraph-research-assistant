export default function OutputDisplay({ output, isStreaming }) {
  return (
    <div className="output-display">
      {isStreaming ? (
        <StreamingDisplay output={output} />
      ) : (
        <OutputDisplay output={output} />
      )}
    </div>
  );
}