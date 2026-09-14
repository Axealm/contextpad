export type EmailLink = {
  provider: "gmail"; provider_message_id?: string | null; received_at?: string | null;
  subject: string; sender: string; snippet: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public status: number, public code: string) { super(code); }
}

export async function request<T>(path: string, method = "GET", data?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method, credentials: "include",
    ...(data === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    signal: AbortSignal.timeout(path.startsWith("/api/v1/gmail/messages?") ? 120000 : 30000),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(response.status, typeof body.detail === "string" ? body.detail : "request_failed");
  }
  return response.status === 204 ? undefined as T : response.json();
}
