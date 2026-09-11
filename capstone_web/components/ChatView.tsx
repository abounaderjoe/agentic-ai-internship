"use client";

import { useEffect, useRef, useState } from "react";
import { getMessages, sendMessage } from "@/lib/api";
import type { ChatMessageItem } from "@/lib/types";
import { ChartMessage } from "./ChartMessage";

export function ChatView({
  chatId,
  onTitleChange,
}: {
  chatId: string;
  onTitleChange: (chatId: string, title: string) => void;
}) {
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    setMessages([]);
    setPendingText(null);
    getMessages(chatId)
      .then(setMessages)
      .finally(() => setLoading(false));
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingText]);

  async function handleSend(text: string) {
    // Show the user's message immediately, before the agent responds.
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setPendingText("");

    let finalText = "";
    const chartsThisTurn: ChatMessageItem[] = [];

    for await (const evt of sendMessage(chatId, text)) {
      if (evt.event === "title") {
        onTitleChange(chatId, evt.data.title);
      } else if (evt.event === "token") {
        finalText += evt.data.text;
        setPendingText(finalText);
      } else if (evt.event === "chart") {
        chartsThisTurn.push({ role: "chart", spec: evt.data });
      } else if (evt.event === "done") {
        setMessages((prev) => [...prev, ...chartsThisTurn, { role: "assistant", content: finalText }]);
        setPendingText(null);
      }
    }
  }

  return (
    <div className="flex h-full flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <h1 className="mb-1 text-2xl font-bold">Multi-Agent Assistant</h1>
        <p className="mb-6 text-sm text-neutral-500">
          A Supervisor routes each message to the right specialist agent. Each chat keeps its own memory.
        </p>

        {loading && <div className="text-sm text-neutral-400">Loading…</div>}

        <div className="flex flex-col gap-4">
          {messages.map((m, i) =>
            m.role === "chart" ? (
              <ChartMessage key={i} spec={m.spec} />
            ) : (
              <MessageBubble key={i} role={m.role} content={m.content} />
            )
          )}
          {pendingText !== null && <MessageBubble role="assistant" content={pendingText + "▌"} />}
        </div>
        <div ref={bottomRef} />
      </div>

      <ChatInput onSend={handleSend} disabled={pendingText !== null} />
    </div>
  );
}

function MessageBubble({ role, content }: { role: "user" | "assistant"; content: string }) {
  const isUser = role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-xl whitespace-pre-wrap rounded-lg px-4 py-2 text-sm ${
          isUser
            ? "bg-indigo-600 text-white"
            : "bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100"
        }`}
      >
        {content}
      </div>
    </div>
  );
}

function ChatInput({ onSend, disabled }: { onSend: (text: string) => void; disabled: boolean }) {
  const [value, setValue] = useState("");

  function submit() {
    const text = value.trim();
    if (!text || disabled) return;
    setValue("");
    onSend(text);
  }

  return (
    <div className="border-t border-black/10 p-4 dark:border-white/10">
      <div className="flex gap-2">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask about sales data, request a chart, research something, or just chat..."
          disabled={disabled}
          className="flex-1 rounded-md border border-black/10 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 disabled:opacity-50 dark:border-white/10 dark:bg-neutral-900"
        />
        <button
          onClick={submit}
          disabled={disabled}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
