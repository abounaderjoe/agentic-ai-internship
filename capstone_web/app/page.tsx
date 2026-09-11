"use client";

import { useEffect, useState } from "react";
import { ChatView } from "@/components/ChatView";
import { Sidebar } from "@/components/Sidebar";
import { createChat, deleteChat, listChats } from "@/lib/api";
import type { ChatSummary } from "@/lib/types";

export default function Home() {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    listChats().then(async (existing) => {
      if (existing.length > 0) {
        setChats(existing);
        setActiveChatId(existing[existing.length - 1].id);
      } else {
        const chat = await createChat();
        setChats([chat]);
        setActiveChatId(chat.id);
      }
      setReady(true);
    });
  }, []);

  async function handleNewChat() {
    const chat = await createChat();
    setChats((prev) => [...prev, chat]);
    setActiveChatId(chat.id);
  }

  function handleTitleChange(chatId: string, title: string) {
    setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, title } : c)));
  }

  async function handleDeleteChat(chatId: string) {
    const chat = chats.find((c) => c.id === chatId);
    if (!window.confirm(`Delete "${chat?.title ?? "this chat"}"? This can't be undone.`)) return;

    await deleteChat(chatId);
    const remaining = chats.filter((c) => c.id !== chatId);
    setChats(remaining);

    if (activeChatId === chatId) {
      if (remaining.length > 0) {
        setActiveChatId(remaining[remaining.length - 1].id);
      } else {
        const chat = await createChat();
        setChats([chat]);
        setActiveChatId(chat.id);
      }
    }
  }

  if (!ready || !activeChatId) {
    return <div className="p-6 text-sm text-neutral-400">Loading…</div>;
  }

  return (
    <div className="flex h-screen">
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={setActiveChatId}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
      />
      <ChatView key={activeChatId} chatId={activeChatId} onTitleChange={handleTitleChange} />
    </div>
  );
}
