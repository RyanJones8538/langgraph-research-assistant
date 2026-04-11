const API_BASE = "/api";

async function postJson(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request failed (${response.status}): ${text}`);
  }
  return response.json();
}

/**
 * Async generator that POSTs to an SSE endpoint and yields each parsed event
 * object as it arrives. SSE lines look like:  data: {"type": "status_update", ...}
 *
 * EventSource only supports GET, so we use fetch + a ReadableStream reader
 * instead. The buffer handles the case where a single network chunk contains
 * partial lines or multiple lines at once.
 */
async function* streamPostSSE(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Request failed (${response.status}): ${text}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? ""; // keep the last (possibly incomplete) line
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const text = line.slice(6).trim();
          if (text) yield JSON.parse(text);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function startRun(topic, threadId) {
  return postJson("/start_run", { topic, thread_id: threadId });
}

export function resumeRun(threadId, userReply) {
  return postJson("/resume_run", { thread_id: threadId, user_reply: userReply });
}

export function streamStartRun(topic, threadId) {
  return streamPostSSE("/stream_run", { topic, thread_id: threadId });
}

export function streamResumeRun(threadId, userReply) {
  return streamPostSSE("/stream_resume", { thread_id: threadId, user_reply: userReply });
}