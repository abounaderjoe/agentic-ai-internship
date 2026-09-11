"use client";

import { useEffect, useState } from "react";
import { ChatView } from "@/components/ChatView";
import { Sidebar } from "@/components/Sidebar";
import { createChat, listChats } from "@/lib/api";
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

  if (!ready || !activeChatId) {
    return <div className="p-6 text-sm text-neutral-400">Loading…</div>;
  }

  return (
    <div className="flex h-screen">
      <Sidebar chats={chats} activeChatId={activeChatId} onSelectChat={setActiveChatId} onNewChat={handleNewChat} />
      <ChatView key={activeChatId} chatId={activeChatId} onTitleChange={handleTitleChange} />
    </div>
  );
}
