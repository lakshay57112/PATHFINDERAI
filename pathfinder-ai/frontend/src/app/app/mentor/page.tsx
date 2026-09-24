"use client";

import { ChatPanel } from "@/components/mentor/chat-panel";

export default function MentorPage() {
  return (
    <div className="flex h-[calc(100dvh-9rem)] flex-col md:h-[calc(100dvh-8rem)] lg:h-[calc(100dvh-6.5rem)]">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <p className="eyebrow mb-2">AI Mentor</p>
          <h1 className="text-[28px] font-semibold tracking-tight">Your career mentor</h1>
        </div>
        <p className="hidden max-w-xs text-right text-[12.5px] text-muted md:block">
          It can adjust your roadmap when you ask. Guidance only — no guarantees about jobs or salaries.
        </p>
      </div>
      <div className="min-h-0 flex-1"><ChatPanel /></div>
    </div>
  );
}
