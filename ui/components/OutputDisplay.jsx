import ReactMarkdown from "react-markdown";

function tryParseJsonObject(text) {
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
  } catch {}
  return null;
}

function reportToMarkdown(content) {
  const data =
    content && typeof content === "object"
      ? content
      : tryParseJsonObject(String(content));

  if (!data || !Array.isArray(data.sections)) return String(content);

  return data.sections
    .map((section) => {
      const lines = [`# ${section.title}`];
      if (section.text) lines.push("", section.text);
      section.subsections?.forEach((sub) => {
        lines.push("", `## ${sub.title}`);
        if (sub.text) lines.push("", sub.text);
      });
      return lines.join("\n");
    })
    .join("\n\n");
}

function downloadMarkdown(content) {
  const md = reportToMarkdown(content);
  const blob = new Blob([md], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "report.md";
  a.click();
  URL.revokeObjectURL(url);
}

function OutlineJsonDisplay({ data }) {
  return (
    <div>
      {Object.entries(data).map(([section, subsections]) => (
        <div key={section} style={{ marginBottom: "0.6rem" }}>
          <strong>{section}</strong>
          {Array.isArray(subsections) && subsections.length > 0 && (
            <ul style={{ margin: "0.2rem 0 0 1.25rem", padding: 0 }}>
              {subsections.map((sub, i) => (
                <li key={i} style={{ fontSize: "0.9rem" }}>{sub}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function OutlineTextDisplay({ text }) {
  const lines = text.split("\n").filter((line) => line.trim());
  return (
    <div>
      {lines.map((line, i) => {
        const isSectionHeader = /^\d+\./.test(line.trim()) && !/^\s/.test(line);
        return isSectionHeader ? (
          <div key={i} style={{ marginTop: "0.5rem" }}>
            <strong>{line}</strong>
          </div>
        ) : (
          <div key={i} style={{ marginLeft: "1.25rem", fontSize: "0.9rem" }}>
            {line.trim()}
          </div>
        );
      })}
    </div>
  );
}

function isOutlineTextFormat(text) {
  return /^1\.\s/.test(text.trimStart());
}

function FinalReportDisplay({ data }) {
  return (
    <div>
      {data.sections.map((section, i) => (
        <div key={i} style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ margin: "0 0 0.4rem" }}>{section.title}</h2>
          {section.text && <ReactMarkdown>{section.text}</ReactMarkdown>}
          {section.subsections.map((sub, j) => (
            <div key={j} style={{ marginBottom: "0.8rem", marginLeft: "1.25rem" }}>
              <h3 style={{ margin: "0 0 0.3rem" }}>{sub.title}</h3>
              {sub.text && <ReactMarkdown>{sub.text}</ReactMarkdown>}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function ContentDisplay({ content }) {
  // Already a parsed object (final_report dict passed directly from state)
  if (content && typeof content === "object") {
    if (Array.isArray(content.sections)) return <FinalReportDisplay data={content} />;
    return <OutlineJsonDisplay data={content} />;
  }

  const text = String(content);
  const parsed = tryParseJsonObject(text);
  if (parsed) {
    if (Array.isArray(parsed.sections)) return <FinalReportDisplay data={parsed} />;
    return <OutlineJsonDisplay data={parsed} />;
  }

  if (isOutlineTextFormat(text)) return <OutlineTextDisplay text={text} />;

  return <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{text}</pre>;
}

function StatusLog({ statusHistory, isRunning }) {
  return (
    <div>
      {statusHistory.map((entry, i) => (
        <div
          key={i}
          style={{
            fontSize: "0.9rem",
            marginBottom: "0.3rem",
            color: i === statusHistory.length - 1 ? "inherit" : "#777",
          }}
        >
          {entry}
        </div>
      ))}
      {isRunning && <span style={{ color: "#aaa" }}>…</span>}
    </div>
  );
}

export default function OutputDisplay({ output, statusHistory, runPhase }) {
  const isRunning = runPhase === "running";
  const isComplete = runPhase === "complete";

  return (
    <section>
      <h2>
        Output{" "}
        {isRunning ? (
          <small style={{ fontWeight: "normal", color: "grey" }}>running…</small>
        ) : null}
        {isComplete && output ? (
          <button
            onClick={() => downloadMarkdown(output)}
            style={{ marginLeft: "1rem", fontSize: "0.85rem" }}
          >
            Download .md
          </button>
        ) : null}
      </h2>
      <p>Proposed outlines and the final report should appear here.</p>
      {output ? (
        <ContentDisplay content={output} />
      ) : statusHistory?.length > 0 ? (
        <StatusLog statusHistory={statusHistory} isRunning={isRunning} />
      ) : (
        <p style={{ color: "#888" }}>No output yet.</p>
      )}
    </section>
  );
}
