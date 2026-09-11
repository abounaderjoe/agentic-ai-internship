"use client";

import type { ChatSummary } from "@/lib/types";

const AGENTS = [
  {
    name: "sql_query_agent",
    description: "Answers questions about customers, products, orders, and revenue from the sample sales database.",
  },
  {
    name: "web_research_team",
    description: "Researches a topic on the live web and produces a synthesized report.",
  },
  {
    name: "visualization_agent",
    description: "Creates an interactive bar, pie, or line chart from structured data.",
  },
  {
    name: "rag_agent",
    description: "Answers questions about Groq, LangChain/LCEL, or LangSmith from the internal docs.",
  },
  {
    name: "conversation_agent",
    description: "Handles general chit-chat with no specific data need.",
  },
];

export function Sidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
}: {
  chats: ChatSummary[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
}) {
  return (
    <aside className="flex h-full w-72 shrink-0 flex-col overflow-y-auto border-r border-black/10 bg-neutral-50 p-4 dark:border-white/10 dark:bg-neutral-950">
      <button
        onClick={onNewChat}
        className="mb-4 rounded-md border border-black/10 bg-white px-3 py-2 text-sm font-medium hover:bg-neutral-100 dark:border-white/10 dark:bg-neutral-900 dark:hover:bg-neutral-800"
      >
        + New chat
      </button>

      <div className="mb-2 text-xs font-medium text-neutral-500">Chats</div>
      <div className="mb-6 flex flex-col gap-1">
        {[...chats].reverse().map((c) => (
          <button
            key={c.id}
            onClick={() => onSelectChat(c.id)}
            className={`truncate rounded-md px-3 py-2 text-left text-sm ${
              c.id === activeChatId
                ? "bg-neutral-200 dark:bg-neutral-800"
                : "hover:bg-neutral-100 dark:hover:bg-neutral-900"
            }`}
            title={c.title}
          >
            {c.id === activeChatId ? "● " : ""}
            {c.title}
          </button>
        ))}
      </div>

      <div className="mb-2 text-sm font-semibold">Specialist agents</div>
      <div className="flex flex-col gap-3">
        {AGENTS.map((a) => (
          <div key={a.name} className="text-xs text-neutral-600 dark:text-neutral-400">
            <div className="font-semibold text-neutral-800 dark:text-neutral-200">{a.name}</div>
            <div>{a.description}</div>
          </div>
        ))}
      </div>
    </aside>
  );
}
