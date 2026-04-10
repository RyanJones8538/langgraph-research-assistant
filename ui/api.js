const API_BASE ="/api";

const startRun = async (topic, threadId) => {
  const response = await fetch(`${API_BASE}/start_run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ topic, thread_id: threadId })
  });
  return response.json();
};

const resumeRun = async (threadId, userReply) => {
  const response = await fetch(`${API_BASE}/resume_run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ thread_id: threadId, user_reply: userReply })
  });
  return response.json();
};