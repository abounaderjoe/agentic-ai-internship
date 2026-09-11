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

function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m3 0-1 14a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1L5 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Sidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
}: {
  chats: ChatSummary[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat: (id: string) => void;
}) {
  return (
    <aside className="flex h-full w-64 shrink-0 flex-col bg-neutral-950 text-neutral-200">
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="flex w-full items-center gap-2 rounded-lg border border-neutral-700 px-3 py-2.5 text-sm hover:bg-neutral-800"
        >
          <PlusIcon />
          New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2">
        <div className="px-2 pb-1 pt-2 text-xs font-medium text-neutral-500">Chats</div>
        <div className="flex flex-col gap-0.5">
          {[...chats].reverse().map((c) => (
            <div
              key={c.id}
              className={`group flex items-center rounded-lg pr-1 ${
                c.id === activeChatId ? "bg-neutral-800" : "hover:bg-neutral-800/60"
              }`}
            >
              <button
                onClick={() => onSelectChat(c.id)}
                className="min-w-0 flex-1 truncate px-2 py-2 text-left text-sm"
                title={c.title}
              >
                {c.title}
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteChat(c.id);
                }}
                className="hidden shrink-0 rounded p-1.5 text-neutral-400 hover:bg-neutral-700 hover:text-red-400 group-hover:block"
                title="Delete chat"
              >
                <TrashIcon />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-neutral-800 p-3">
        <div className="mb-2 text-xs font-semibold text-neutral-400">Specialist agents</div>
        <div className="flex flex-col gap-2.5">
          {AGENTS.map((a) => (
            <div key={a.name} className="text-xs text-neutral-500">
              <div className="font-medium text-neutral-300">{a.name}</div>
              <div>{a.description}</div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
