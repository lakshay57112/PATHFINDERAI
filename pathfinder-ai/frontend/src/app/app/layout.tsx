"use client";

import { MessageCircle } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ChatPanel } from "@/components/mentor/chat-panel";
import { MobileNav, MobileTopBar, Sidebar } from "@/components/shell/nav";
import { Dialog, DialogDescription, DialogTitle, SheetContent } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api";
import { useMe } from "@/lib/queries";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const me = useMe();
  const router = useRouter();
  const path = usePathname();
  const [mentorOpen, setMentorOpen] = useState(false);

  useEffect(() => {
    if (me.error instanceof ApiError && me.error.status === 401) router.replace(`/login?next=${encodeURIComponent(path)}`);
    else if (me.data && !me.data.onboarding_completed) router.replace("/onboarding");
  }, [me.error, me.data, router, path]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setMentorOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!me.data || !me.data.onboarding_completed) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <div className="size-1.5 animate-ping rounded-full bg-ink" aria-label="Loading" />
      </div>
    );
  }

  return (
    <div className="min-h-dvh">
      <Sidebar />
      <MobileTopBar />
      <main className="lg:pl-[248px]">
        <div className="mx-auto w-full max-w-[1120px] px-5 pb-32 pt-10 sm:px-8 md:pt-16 lg:px-12 lg:pb-24">{children}</div>
      </main>
      <MobileNav />

      {path !== "/app/mentor" && (
        <button
          onClick={() => setMentorOpen(true)}
          className="focus-ring fixed bottom-6 right-6 z-30 hidden items-center gap-2 rounded-full bg-ink py-3 pl-4 pr-5 text-[14px] font-medium text-white shadow-lift transition-transform hover:scale-[1.02] active:scale-[0.98] lg:inline-flex"
          aria-label="Open AI mentor"
        >
          <MessageCircle className="size-4" /> Ask your mentor
          <span className="ml-1 rounded bg-white/15 px-1.5 font-mono text-[11px]">⌘K</span>
        </button>
      )}
      <Dialog open={mentorOpen} onOpenChange={setMentorOpen}>
        <SheetContent>
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <div>
              <DialogTitle className="text-[15px] font-semibold">AI Mentor</DialogTitle>
              <DialogDescription className="text-[12px] text-muted">Grounded in your profile and roadmap</DialogDescription>
            </div>
            <button onClick={() => setMentorOpen(false)} className="focus-ring rounded-md px-2 py-1 text-[13px] text-fg-2 hover:bg-surface-2">Close</button>
          </div>
          <div className="min-h-0 flex-1"><ChatPanel compact /></div>
        </SheetContent>
      </Dialog>
    </div>
  );
}
