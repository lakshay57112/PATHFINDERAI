"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, BookMarked, RotateCcw, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ApiError, get, stream } from "@/lib/api";
import { useInvalidatePlan } from "@/lib/queries";
import type { Source } from "@/lib/types";
import { cn } from "@/lib/utils";

type Msg = { role: "user" | "assistant"; content: string; sources?: Source[]; action?: any; pending?: boolean; error?: boolean };

const ACTION_LABEL: Record<string, string> = {
  roadmap_updated: "Roadmap updated",
  hours_updated: "Availability updated",
  evidence_added: "Evidence saved",
};

export function ChatPanel({ compact = false, sessionId: initialSession }: { compact?: boolean; sessionId?: string }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSession);
  const [aiInfo, setAiInfo] = useState<{ ai: boolean; model: string } | null>(null);
  const abort = useRef<AbortController | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const invalidate = useInvalidatePlan();
  const { data: sugg } = useQuery({ queryKey: ["mentor-suggestions"], queryFn: () => get<{ suggestions: string[] }>("/mentor/suggestions"), staleTime: Infinity });

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    const msg = text.trim();
    if (!msg || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: msg }, { role: "assistant", content: "", pending: true }]);
    const ctrl = new AbortController();
    abort.current = ctrl;
    const patchLast = (fn: (m: Msg) => Msg) => setMessages((ms) => [...ms.slice(0, -1), fn(ms[ms.length - 1])]);
    try {
      await stream("/mentor/chat", { message: msg, session_id: sessionId }, (e) => {
        if (e.event === "meta") {
          setSessionId(e.data.session_id);
          setAiInfo({ ai: e.data.ai, model: e.data.model });
          patchLast((m) => ({ ...m, sources: e.data.sources, action: e.data.action }));
          if (e.data.action) invalidate();
        } else if (e.event === "token") {
          patchLast((m) => ({ ...m, content: m.content + e.data.t, pending: false }));
        } else if (e.event === "error") {
          patchLast((m) => ({ ...m, content: e.data.message, pending: false, error: true }));
        }
      }, ctrl.signal);
    } catch (err) {
      patchLast((m) => ({ ...m, content: err instanceof ApiError ? err.message : "Something went wrong.", pending: false, error: true }));
    } finally {
      patchLast((m) => ({ ...m, pending: false }));
      setBusy(false);
    }
  };

  const reset = () => {
    abort.current?.abort();
    setMessages([]);
    setSessionId(undefined);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div ref={scroller} className={cn("flex-1 overflow-y-auto", compact ? "px-5 py-5" : "px-1 py-2")}>
        {messages.length === 0 ? (
          <div className={cn("flex h-full flex-col justify-end", compact ? "pb-2" : "pb-6")}>
            <p className="eyebrow mb-3">Your AI career mentor</p>
            <p className={cn("font-semibold tracking-[-0.02em]", compact ? "text-[22px]" : "text-[30px]")}>How can I help you move forward?</p>
            <p className="mt-2 max-w-md text-[14px] leading-relaxed text-fg-2">I know your profile and roadmap. I can explain skills, suggest projects, quiz you, and adjust your plan when life changes.</p>
            <div className="mt-6 flex flex-wrap gap-2">
              {(sugg?.suggestions ?? []).map((s) => (
                <button key={s} onClick={() => send(s)} className="focus-ring rounded-full border border-line-strong bg-surface px-3.5 py-1.5 text-left text-[13px] text-fg-2 transition-colors hover:border-ink hover:text-fg">
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            <AnimatePresence initial={false}>
              {messages.map((m, i) => (
                <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
                  className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                  {m.role === "user" ? (
                    <div className="max-w-[85%] rounded-2xl rounded-br-md bg-ink px-4 py-2.5 text-[14.5px] leading-relaxed text-white">{m.content}</div>
                  ) : (
                    <div className="w-full max-w-[92%]">
                      {m.action && (
                        <div className="mb-2 inline-flex items-center gap-1.5 rounded-md border border-line bg-surface px-2 py-0.5 text-[12px] text-fg-2">
                          <span className="size-1.5 rounded-full bg-success" /> {ACTION_LABEL[m.action.type] ?? "Updated"}
                        </div>
                      )}
                      {m.pending ? (
                        <div className="flex gap-1 py-3" aria-label="Mentor is thinking">
                          {[0, 1, 2].map((d) => <span key={d} className="size-1.5 animate-pulse rounded-full bg-muted" style={{ animationDelay: `${d * 150}ms` }} />)}
                        </div>
                      ) : (
                        <div className={cn("prose-mentor text-[14.5px] text-fg", m.error && "text-danger")}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: (p) => <a {...p} target="_blank" rel="noreferrer" /> }}>{m.content}</ReactMarkdown>
                        </div>
                      )}
                      {!!m.sources?.length && !m.pending && (
                        <details className="group mt-3">
                          <summary className="focus-ring inline-flex cursor-pointer list-none items-center gap-1.5 rounded text-[12px] text-muted hover:text-fg">
                            <BookMarked className="size-3.5" /> {m.sources.length} sources from the PathFinder knowledge base
                          </summary>
                          <ol className="mt-2 space-y-1.5 border-l border-line pl-3">
                            {m.sources.map((s) => (
                              <li key={s.id} className="text-[12.5px] text-fg-2">
                                <span className="font-mono text-muted">[{s.n}]</span>{" "}
                                {s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="underline decoration-line-strong underline-offset-2 hover:text-fg">{s.title}</a> : s.title}
                                <span className="text-muted"> · {s.type}</span>
                              </li>
                            ))}
                          </ol>
                        </details>
                      )}
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <div className={cn("border-t border-line bg-background/80 backdrop-blur", compact ? "p-4" : "pt-4")}>
        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
            rows={1}
            placeholder="Ask about skills, projects, your roadmap…"
            aria-label="Message the mentor"
            className="focus-ring block max-h-40 min-h-[52px] w-full resize-none rounded-xl border border-line-strong bg-surface py-3.5 pl-4 pr-14 text-[15px] placeholder:text-muted focus-visible:border-ink focus-visible:ring-0"
          />
          <div className="absolute bottom-2 right-2">
            {busy ? (
              <Button type="button" size="icon" variant="secondary" onClick={() => abort.current?.abort()} aria-label="Stop"><Square className="!size-3" /></Button>
            ) : (
              <Button type="submit" size="icon" disabled={!input.trim()} aria-label="Send"><ArrowUp /></Button>
            )}
          </div>
        </form>
        <div className="mt-2 flex items-center justify-between text-[11.5px] text-muted">
          <span>{aiInfo ? (aiInfo.ai ? `AI: ${aiInfo.model}` : "Offline mode · answers from your plan and the knowledge base") : "Uses your profile, roadmap and PathFinder's knowledge base"}</span>
          {messages.length > 0 && (
            <button onClick={reset} className="focus-ring inline-flex items-center gap-1 rounded hover:text-fg"><RotateCcw className="size-3" /> New chat</button>
          )}
        </div>
      </div>
    </div>
  );
}
