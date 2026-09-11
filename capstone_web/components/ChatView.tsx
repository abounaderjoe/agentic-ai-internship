"use client";

import { useEffect, useRef, useState } from "react";
import { getMessages, sendMessage } from "@/lib/api";
import type { ChatMessageItem } from "@/lib/types";
import { ChartMessage } from "./ChartMessage";

function ArrowUpIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M12 19V5M5 12l7-7 7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

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
  // True once the user has sent a message in this chat's current mount --
  // guards against the initial getMessages() load resolving late (after a
  // send already updated state) and clobbering it with stale/empty data.
  // Real bug, reproduced: a slow initial fetch landed after a full
  // send-and-respond cycle and blew away the up-to-date messages.
  const hasSentRef = useRef(false);

  useEffect(() => {
    hasSentRef.current = false;
    setLoading(true);
    setMessages([]);
    setPendingText(null);
    getMessages(chatId)
      .then((m) => {
        if (!hasSentRef.current) setMessages(m);
      })
      .finally(() => setLoading(false));
  }, [chatId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pendingText]);

  async function handleSend(text: string) {
    hasSentRef.current = true;
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

  const isEmpty = !loading && messages.length === 0 && pendingText === null;

  return (
    <div className="flex h-full flex-1 flex-col bg-neutral-900">
      {isEmpty ? (
        <div className="flex flex-1 flex-col items-center justify-center px-4">
          <h1 className="mb-6 text-2xl font-semibold text-neutral-200">What can I help with?</h1>
          <div className="w-full max-w-3xl">
            <ChatInput onSend={handleSend} disabled={false} />
          </div>
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8">
              {loading && <div className="text-sm text-neutral-500">Loading…</div>}
              {messages.map((m, i) =>
                m.role === "chart" ? (
                  <ChartMessage key={i} spec={m.spec} />
                ) : (
                  <MessageBubble key={i} role={m.role} content={m.content} />
                )
              )}
              {pendingText !== null && <MessageBubble role="assistant" content={pendingText + "▌"} />}
              <div ref={bottomRef} />
            </div>
          </div>
          <div className="mx-auto w-full max-w-3xl px-4 pb-6">
            <ChatInput onSend={handleSend} disabled={pendingText !== null} />
          </div>
        </>
      )}
    </div>
  );
}

function MessageBubble({ role, content }: { role: "user" | "assistant"; content: string }) {
  if (role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-neutral-700 px-4 py-2.5 text-[15px] text-neutral-50">
          {content}
        </div>
      </div>
    );
  }
  return <div className="whitespace-pre-wrap text-[15px] leading-relaxed text-neutral-100">{content}</div>;
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
    <div className="flex items-end gap-2 rounded-3xl border border-neutral-700 bg-neutral-800 px-4 py-3 shadow-lg">
      <textarea
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
        rows={1}
        className="max-h-48 flex-1 resize-none bg-transparent text-[15px] text-neutral-100 placeholder-neutral-500 outline-none disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-neutral-900 disabled:opacity-30"
      >
        <ArrowUpIcon />
      </button>
    </div>
  );
}
