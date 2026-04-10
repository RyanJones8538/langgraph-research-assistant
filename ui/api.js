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

export function startRun(topic, threadId) {
  return postJson("/start_run", { topic, thread_id: threadId });
}

export function resumeRun(threadId, userReply) {
  return postJson("/resume_run", { thread_id: threadId, user_reply: userReply });
}