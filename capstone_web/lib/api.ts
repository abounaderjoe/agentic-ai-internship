import type { ChartSpec, ChatMessageItem, ChatSummary } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function listChats(): Promise<ChatSummary[]> {
  const res = await fetch(`${API_URL}/chats`);
  if (!res.ok) throw new Error(`listChats failed: ${res.status}`);
  return res.json();
}

export async function createChat(): Promise<ChatSummary> {
  const res = await fetch(`${API_URL}/chats`, { method: "POST" });
  if (!res.ok) throw new Error(`createChat failed: ${res.status}`);
  return res.json();
}

export async function getMessages(chatId: string): Promise<ChatMessageItem[]> {
  const res = await fetch(`${API_URL}/chats/${chatId}/messages`);
  if (!res.ok) throw new Error(`getMessages failed: ${res.status}`);
  return res.json();
}

export async function deleteChat(chatId: string): Promise<void> {
  const res = await fetch(`${API_URL}/chats/${chatId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`deleteChat failed: ${res.status}`);
}

export type StreamEvent =
  | { event: "title"; data: { title: string } }
  | { event: "token"; data: { text: string } }
  | { event: "chart"; data: ChartSpec }
  | { event: "done"; data: Record<string, never> };

/** Parses the backend's Server-Sent Events stream for one sent message.
 * fetch+ReadableStream instead of EventSource, since EventSource can't do
 * POST requests (and we need to send the message body). */
export async function* sendMessage(chatId: string, message: string): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_URL}/chats/${chatId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok || !res.body) throw new Error(`sendMessage failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // Normalize \r\n to \n first: sse-starlette emits \r\n line endings,
    // and a bare "\n\n" boundary search never matches "\r\n\r\n" (no two
    // consecutive \n characters in it), which silently drops the whole
    // buffer once the stream ends.
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      let eventName = "message";
      let dataLines: string[] = [];
      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (dataLines.length === 0) continue;
      const data = JSON.parse(dataLines.join("\n"));
      yield { event: eventName, data } as StreamEvent;
    }
  }
}
