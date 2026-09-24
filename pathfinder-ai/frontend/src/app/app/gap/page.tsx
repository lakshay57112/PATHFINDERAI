"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/motion";
import { Badge } from "@/components/ui/primitives";
import { SegmentBar } from "@/components/ui/segment-bar";
import { ErrorState, LoadingBlock, NeedsTarget } from "@/components/ui/states";
import { ApiError } from "@/lib/api";
import { useGap } from "@/lib/queries";
import type { GapItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const TONE: Record<string, "default" | "success" | "warning" | "muted"> = { strong: "success", developing: "default", needs_development: "warning", not_explored: "muted" };

function GapInner() {
  const fresh = useSearchParams().get("fresh") === "1";
  const { data, isLoading, error, refetch } = useGap();
  if (isLoading) return <LoadingBlock rows={4} />;
  if (error instanceof ApiError && error.code === "no_target_career") return <NeedsTarget />;
  if (error || !data) return <ErrorState error={error} retry={refetch} />;
  const priority = new Set(data.priority_gaps);

  return (
    <div>
      <header className="mb-14">
        <Reveal><p className="eyebrow mb-6">Skill gap analysis</p></Reveal>
        <Reveal delay={0.05}>
          <div className="grid items-end gap-4 md:grid-cols-[1fr_auto_1fr]">
            <div><p className="eyebrow mb-2">Your current profile</p><p className="text-[28px] font-semibold tracking-tight">You, today</p></div>
            <p className="font-mono text-[13px] text-muted md:pb-2">VS</p>
            <div className="md:text-right"><p className="eyebrow mb-2">Target career</p><p className="text-[28px] font-semibold tracking-tight">{data.career_name}</p></div>
          </div>
        </Reveal>
        <Reveal delay={0.1} className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-4">
          {[["Strong", data.counts.strong], ["Developing", data.counts.developing], ["Needs development", data.counts.needs_development], ["Not yet explored", data.counts.not_explored]].map(([l, n]) => (
            <div key={l as string} className="bg-surface p-5"><p className="text-[28px] font-semibold tabular-nums tracking-tight">{n}</p><p className="text-[13px] text-fg-2">{l}</p></div>
          ))}
        </Reveal>
      </header>

      <div className="grid gap-12 lg:grid-cols-[1fr_300px]">
        <div className="divide-y divide-line border-y border-line">
          {data.items.map((it, i) => <GapRow key={it.skill_id} it={it} priority={priority.has(it.name)} index={i} />)}
        </div>
        <aside className="space-y-8 lg:sticky lg:top-10 lg:h-fit">
          <div>
            <p className="eyebrow mb-3">Current strengths</p>
            <p className="text-[17px] font-medium leading-snug">{data.strengths.join(" · ") || "—"}</p>
          </div>
          <div>
            <p className="eyebrow mb-3">Priority gaps</p>
            <p className="text-[17px] font-medium leading-snug">{data.priority_gaps.join(" · ") || "None — nice."}</p>
          </div>
          <p className="text-[13px] leading-relaxed text-muted">{data.note}</p>
          <Button asChild size="lg" className="w-full"><Link href="/app/roadmap">{fresh ? "See my roadmap" : "Open roadmap"} <ArrowRight /></Link></Button>
        </aside>
      </div>
    </div>
  );
}

function GapRow({ it, priority, index }: { it: GapItem; priority: boolean; index: number }) {
  const [open, setOpen] = useState(priority && index < 2);
  const e = it.explanation;
  return (
    <div className="py-5" data-index={index}>
      <button type="button" disabled={!e} onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="focus-ring flex w-full flex-wrap items-center gap-x-6 gap-y-3 rounded-lg text-left">
        <div className="min-w-0 flex-1 md:w-[210px] md:flex-none">
          <p className="flex items-center gap-2 text-[16px] font-medium">
            {it.name}
            {priority && <span className="size-1.5 rounded-full bg-ink" title="Priority gap" />}
          </p>
          <p className="text-[12px] text-muted">{it.importance} · target {it.target_label.toLowerCase()}</p>
        </div>
        <div className="order-last w-full md:order-none md:w-auto md:flex-1"><SegmentBar value={it.bar} /></div>
        <div className="flex items-center justify-end gap-2 md:w-[180px]">
          <Badge tone={TONE[it.status]}>{it.status_label}</Badge>
          {e ? <ChevronDown className={cn("size-4 text-muted transition-transform", open && "rotate-180")} /> : <span className="w-4" />}
        </div>
      </button>
      <AnimatePresence initial={false}>
        {open && e && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }} className="overflow-hidden">
            <div className="mt-5 grid gap-5 rounded-xl bg-surface p-5 ring-1 ring-line md:grid-cols-2">
              <Detail label="Why it matters">{e.why_it_matters}</Detail>
              <Detail label="What to learn">
                {e.what_to_learn}
                <ul className="mt-2 space-y-1">{e.resources.map((r) => <li key={r.title}><a href={r.url ?? "#"} target="_blank" rel="noreferrer" className="underline decoration-line-strong underline-offset-2 hover:decoration-black">{r.title}</a> <span className="text-muted">· {r.provider}</span></li>)}</ul>
              </Detail>
              <Detail label="Suggested practice">{e.suggested_practice}</Detail>
              <Detail label="Suggested project">{e.suggested_project ? <Link href="/app/projects" className="underline underline-offset-2">{e.suggested_project.name}</Link> : "—"}</Detail>
              {e.optional_certificate && (
                <Detail label="Optional certificate">{e.optional_certificate.name} <span className="text-muted">· {e.optional_certificate.provider}</span></Detail>
              )}
              <Detail label="Current evidence">
                {it.evidence.length ? it.evidence.map((x) => x.title).join(" · ") : "None yet"}
              </Detail>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><p className="eyebrow mb-1.5">{label}</p><div className="text-[14px] leading-relaxed text-fg-2">{children}</div></div>;
}

export default function GapPage() {
  return <Suspense><GapInner /></Suspense>;
}
