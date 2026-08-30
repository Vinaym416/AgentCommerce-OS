export const API_BASE_URL = "http://127.0.0.1:8000";

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