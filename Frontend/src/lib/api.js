export const API_BASE_URL = "http://127.0.0.1:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, "ws");

export async function apiRequest(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      (data && (data.detail || data.message)) ||
      "Request failed";

    throw new Error(message);
  }

  return data;
}




export async function sendCommerceMessage(payload = {}) {
  return apiRequest("/commerce/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createCommerceSocket({ onOpen, onMessage, onError, onClose } = {}) {
  const socket = new WebSocket(`${WS_BASE_URL}/commerce/chat/ws`);

  socket.addEventListener("open", onOpen);
  socket.addEventListener("message", (event) => {
    try {
      onMessage?.(JSON.parse(event.data));
    } catch {
      onError?.(new Error("The chat server returned an invalid WebSocket message."));
    }
  });
  socket.addEventListener("error", onError);
  socket.addEventListener("close", onClose);

  return socket;
}

export async function getChatSession(sessionId) {
  return apiRequest(`/commerce/chat/session/${encodeURIComponent(sessionId)}`);
}