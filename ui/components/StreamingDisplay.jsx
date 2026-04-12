const NODE_LABELS = {
  generate_outline: "Generating Outline",
  parse_review: "Parsing Review",
  generate_questions: "Generating Research Questions",
  search_sources: "Searching Sources",
  evaluate_sources: "Evaluating Sources",
  identify_gaps: "Identifying Gaps",
  writer: "Writing Report",
  editor: "Editing Report",
  initialize: "Initializing",
  initialize_research: "Initializing Research",
  initialize_writer: "Initializing Writer",
};

function isOutlineTextFormat(text) {
  return /^1\.\s/.test(text.trimStart());
}

function isSourceObject(obj) {
  return (
    typeof obj === "object" &&
    obj !== null &&
    typeof obj.title === "string" &&
    typeof obj.url === "string" &&
    typeof obj.domain === "string"
  );
}

function OutlineTextDisplay({ text }) {
  const lines = text.split("\n").filter((line) => line.trim());
  return (
    <div>
      {lines.map((line, i) => {
        const isSectionHeader = /^\d+\./.test(line.trim()) && !/^\s/.test(line);
        return isSectionHeader ? (
          <div key={i} style={{ fontWeight: "bold", marginTop: "0.4rem", fontSize: "0.9rem" }}>
            {line}
          </div>
        ) : (
          <div key={i} style={{ paddingLeft: "1.25rem", fontSize: "0.85rem", color: "#333" }}>
            {line.trim()}
          </div>
        );
      })}
    </div>
  );
}

function FieldValue({ value, depth = 0 }) {
  if (value === null || value === undefined) {
    return <span style={{ color: "#888", fontSize: "0.9rem" }}>—</span>;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return <span style={{ color: "#888", fontSize: "0.9rem" }}>[ ]</span>;
    return (
      <div style={{ paddingLeft: "0.5rem" }}>
        {value.map((item, i) => {
          if (isSourceObject(item)) {
            const { title, ...rest } = item;
            return (
              <div key={i} style={{ marginBottom: "0.5rem" }}>
                <div style={{ fontWeight: "bold", fontSize: "0.85rem" }}>{title}</div>
                <div style={{ paddingLeft: "1rem" }}>
                  <FieldValue value={rest} depth={depth + 1} />
                </div>
              </div>
            );
          }
          return (
            <div key={i} style={{ display: "flex", gap: "0.4rem", marginBottom: "0.15rem" }}>
              <span style={{ color: "#aaa", fontSize: "0.85rem", flexShrink: 0 }}>–</span>
              <div style={{ fontSize: "0.85rem" }}>
                {typeof item === "object" && item !== null ? (
                  <FieldValue value={item} depth={depth + 1} />
                ) : typeof item === "string" && item.includes("\n") && isOutlineTextFormat(item) ? (
                  <OutlineTextDisplay text={item} />
                ) : (
                  String(item)
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }
  if (typeof value === "object") {
    return (
      <div style={{ paddingLeft: "0.5rem" }}>
        {Object.entries(value).map(([k, v]) => (
          <div key={k} style={{ marginBottom: "0.4rem" }}>
            <div style={{ fontWeight: "bold", fontSize: depth === 0 ? "0.9rem" : "0.85rem" }}>
              {k}
            </div>
            <div style={{ paddingLeft: "1rem" }}>
              <FieldValue value={v} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "string" && value.includes("\n")) {
    if (isOutlineTextFormat(value)) return <OutlineTextDisplay text={value} />;
    return (
      <pre style={{ margin: "0.2rem 0 0 0", fontSize: "0.85rem", whiteSpace: "pre-wrap", wordBreak: "break-word", color: "#333" }}>
        {value}
      </pre>
    );
  }
  return <span style={{ fontSize: "0.9rem", wordBreak: "break-word", color: "#333" }}>{String(value)}</span>;
}

/**
 * Splits text that may contain one or more concatenated JSON objects into
 * an array of parsed values. Handles nested objects/arrays and quoted strings
 * correctly. Returns null if nothing valid was found.
 */
function splitJsonObjects(text) {
  const results = [];
  let pos = 0;
  const t = text.trimStart();

  while (pos < t.length) {
    while (pos < t.length && /\s/.test(t[pos])) pos++;
    if (pos >= t.length) break;
    const opener = t[pos];
    if (opener !== "{" && opener !== "[") break;
    const closer = opener === "{" ? "}" : "]";

    let depth = 0;
    let inStr = false;
    let esc = false;
    let end = -1;

    for (let i = pos; i < t.length; i++) {
      const c = t[i];
      if (esc) { esc = false; continue; }
      if (c === "\\" && inStr) { esc = true; continue; }
      if (c === '"') { inStr = !inStr; continue; }
      if (inStr) continue;
      if (c === opener) depth++;
      else if (c === closer) {
        depth--;
        if (depth === 0) { end = i; break; }
      }
    }

    if (end === -1) break; // incomplete — still streaming
    try {
      results.push(JSON.parse(t.slice(pos, end + 1)));
    } catch {
      break;
    }
    pos = end + 1;
  }

  return results.length > 0 ? results : null;
}

function ChunkContent({ content }) {
  if (!content) return <span style={{ color: "#888" }}>—</span>;

  const objects = splitJsonObjects(content);
  if (objects) {
    return (
      <div>
        {objects.map((obj, i) => (
          <div key={i} style={{ marginBottom: objects.length > 1 ? "0.6rem" : 0 }}>
            {typeof obj === "object" && !Array.isArray(obj) ? (
              typeof obj.section_title === "string" && Array.isArray(obj.kept_sources) ? (
                // SectionEvidenceResult: section_title as header, sub-fields nested beneath
                <div>
                  <div style={{ fontWeight: "bold", fontSize: "0.9rem" }}>{obj.section_title}</div>
                  <div style={{ paddingLeft: "1rem" }}>
                    {Object.entries(obj)
                      .filter(([k]) => k !== "section_title")
                      .map(([k, v]) => (
                        <div key={k} style={{ marginBottom: "0.4rem" }}>
                          <div style={{ fontWeight: "bold", fontSize: "0.9rem" }}>{k}</div>
                          <div style={{ paddingLeft: "1rem" }}>
                            <FieldValue value={v} depth={0} />
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              ) : typeof obj.section_title === "string" && Array.isArray(obj.questions) ? (
                // SectionQuestions: use section_title as header, questions indented beneath
                <div>
                  <div style={{ fontWeight: "bold", fontSize: "0.9rem" }}>{obj.section_title}</div>
                  <div style={{ paddingLeft: "1rem" }}>
                    <FieldValue value={obj.questions} depth={0} />
                  </div>
                </div>
              ) : (
                Object.entries(obj).map(([k, v]) => (
                  <div key={k} style={{ marginBottom: "0.4rem" }}>
                    <div style={{ fontWeight: "bold", fontSize: "0.9rem" }}>{k}</div>
                    <div style={{ paddingLeft: "1rem" }}>
                      <FieldValue value={v} depth={0} />
                    </div>
                  </div>
                ))
              )
            ) : (
              <FieldValue value={obj} depth={0} />
            )}
          </div>
        ))}
      </div>
    );
  }

  if (isOutlineTextFormat(content)) return <OutlineTextDisplay text={content} />;

  return (
    <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: "0.9rem", margin: 0 }}>
      {content}
    </pre>
  );
}

function TokenDisplay({ chunks }) {
  if (!chunks || chunks.length === 0) {
    return <p style={{ color: "#888" }}>No tokens received yet.</p>;
  }
  return (
    <div>
      {chunks.map((chunk, i) => (
        <div key={i} style={{ marginBottom: "0.8rem" }}>
          <div style={{ fontSize: "0.8rem", fontWeight: "bold", color: "#888", marginBottom: "0.25rem", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            {NODE_LABELS[chunk.node] ?? chunk.node ?? "Unknown node"}
          </div>
          <div style={{ paddingLeft: "1rem", borderLeft: "2px solid #e0e0e0" }}>
            <ChunkContent content={chunk.content} />
          </div>
        </div>
      ))}
    </div>
  );
}

function ParsedFields({ jsonText }) {
  let parsed;
  try {
    parsed = JSON.parse(jsonText);
  } catch {
    return <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{jsonText}</pre>;
  }
  return (
    <div>
      {Object.entries(parsed).map(([key, value]) => (
        <div key={key} style={{ marginBottom: "0.8rem" }}>
          <div style={{ fontWeight: "bold", fontSize: "1rem", marginBottom: "0.25rem" }}>
            {key}
          </div>
          <div style={{ paddingLeft: "1rem", borderLeft: "2px solid #e0e0e0" }}>
            <FieldValue value={value} depth={0} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function StreamingDisplay({ mode, status, streamText, tokenChunks }) {
  return (
    <section>
      <h2>Streaming State</h2>
      <p>
        <strong>Mode:</strong>{" "}
        {mode === "verbose" ? "Verbose" : mode === "tokens" ? "Token stream" : "Basic"}
      </p>
      {mode === "verbose" ? (
        streamText
          ? <ParsedFields jsonText={streamText} />
          : <p style={{ color: "#888" }}>No stream received yet.</p>
      ) : mode === "tokens" ? (
        <TokenDisplay chunks={tokenChunks} />
      ) : (
        <p>{status || <span style={{ color: "#888" }}>No status update yet.</span>}</p>
      )}
    </section>
  );
}
