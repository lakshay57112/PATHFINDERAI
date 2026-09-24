"use client";

import Link from "next/link";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown, Circle, CircleDot, Clock, RefreshCcw, SkipForward } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Reveal } from "@/components/ui/motion";
import { Badge, Input, Label } from "@/components/ui/primitives";
import { ProgressLine } from "@/components/ui/segment-bar";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/ui/states";
import { ApiError } from "@/lib/api";
import { useAdjustRoadmap, useGenerateRoadmap, useRoadmap, useUpdateStep, useVocab } from "@/lib/queries";
import type { RoadmapPhase, RoadmapStep } from "@/lib/types";
import { cn, pad2 } from "@/lib/utils";

export default function RoadmapPage() {
  const { data, isLoading, error, refetch } = useRoadmap();
  const [adjustOpen, setAdjustOpen] = useState(false);
  const regenerate = useGenerateRoadmap();

  if (isLoading) return <LoadingBlock rows={4} />;
  if (error instanceof ApiError && error.status === 404)
    return <EmptyState title="No roadmap yet" description="Choose a direction and we'll build a roadmap around what you already know." action={{ href: "/app/discover", label: "Discover my paths" }} />;
  if (error || !data) return <ErrorState error={error} retry={refetch} />;
  const done = data.skills_total ? data.skills_done / data.skills_total : 0;

  return (
    <div>
      <header className="mb-14">
        <Reveal><p className="eyebrow mb-4">Personalised roadmap · v{data.version}</p></Reveal>
        <Reveal delay={0.05}><h1 className="text-title font-semibold">Your path to {data.career_name}.</h1></Reveal>
        <Reveal delay={0.1} className="mt-8 grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
          <div className="max-w-xl">
            <div className="mb-3 flex items-baseline justify-between text-[14px]">
              <span className="text-fg-2">{data.skills_done} of {data.skills_total} skills</span>
              <span className="font-medium">{data.remaining_label} remaining</span>
            </div>
            <ProgressLine value={done} />
            <p className="mt-3 text-[13px] text-muted">{data.timeline_note}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => setAdjustOpen(true)}><Clock /> {data.hours_per_week} h/week · Adjust</Button>
            <Button variant="ghost" onClick={() => regenerate.mutate({ career_id: data.career_id })} loading={regenerate.isPending}><RefreshCcw /> Recalculate</Button>
          </div>
        </Reveal>
        {(data.switched_from || data.carried_over.length > 0 || data.adjustments.length > 0) && (
          <Reveal delay={0.15} className="mt-8 space-y-1.5 border-l-2 border-ink pl-4 text-[14px] text-fg-2">
            {data.switched_from && <p>Recalculated from your previous direction, <span className="text-fg">{data.switched_from}</span> — not started from zero.</p>}
            {data.carried_over.length > 0 && <p>Carried over: <span className="text-fg">{data.carried_over.join(", ")}</span></p>}
            {data.adjustments.slice(0, 2).map((a) => <p key={a.at}>{a.text}</p>)}
          </Reveal>
        )}
      </header>

      <ol className="relative">
        <div className="absolute bottom-6 left-[15px] top-2 w-px bg-line md:left-[19px]" aria-hidden />
        {data.phases.map((p, i) => <Phase key={p.index} phase={p} index={i} last={i === data.phases.length - 1} />)}
      </ol>

      <AdjustDialog open={adjustOpen} onOpenChange={setAdjustOpen} hours={data.hours_per_week} />
    </div>
  );
}

function Phase({ phase, index, last }: { phase: RoadmapPhase; index: number; last: boolean }) {
  const covered = phase.status === "covered";
  return (
    <li className={cn("relative pl-12 md:pl-16", !last && "pb-14")}>
      <Reveal>
        <span className={cn("absolute left-0 top-0 flex size-8 items-center justify-center rounded-full border bg-background font-mono text-[11px] md:size-10",
          phase.status === "done" || covered ? "border-ink bg-ink text-white" : phase.status === "in_progress" ? "border-ink text-fg" : "border-line-strong text-muted")}>
          {phase.status === "done" || covered ? <Check className="size-4" /> : pad2(index + 1)}
        </span>
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
          <div>
            <p className="eyebrow">Phase {pad2(index + 1)}</p>
            <h2 className="mt-1 text-[24px] font-semibold tracking-tight">{phase.name}</h2>
          </div>
          <p className="font-mono text-[13px] text-fg-2">{phase.duration_label}{!covered && phase.steps.length > 0 && ` · ~${Math.round(phase.est_hours)}h`}</p>
        </div>
        {!covered && phase.steps.length > 0 && <ProgressLine value={phase.progress} className="mt-4 max-w-sm" />}
      </Reveal>

      {phase.covered.length > 0 && (
        <Reveal delay={0.05} className="mt-5 rounded-xl border border-dashed border-line-strong p-4 text-[14px] text-fg-2">
          <span className="font-medium text-fg">Already covered: </span>
          {phase.covered.map((c) => c.name).join(", ")}
          <span className="text-muted"> — you already meet the target level, so these are skipped and you won&apos;t repeat what you know.</span>
        </Reveal>
      )}

      <div className="mt-5 space-y-2">
        {phase.steps.map((s, i) => <StepRow key={s.id} step={s} index={i} />)}
      </div>
    </li>
  );
}

const NEXT_STATUS: Record<string, "in_progress" | "done" | "todo"> = { todo: "in_progress", in_progress: "done", done: "todo", skipped: "todo" };

function StepRow({ step, index }: { step: RoadmapStep; index: number }) {
  const [open, setOpen] = useState(false);
  const update = useUpdateStep();
  const c = step.content;
  const finished = step.status === "done" || step.status === "skipped";
  const Icon = step.status === "done" ? Check : step.status === "skipped" ? SkipForward : step.status === "in_progress" ? CircleDot : Circle;

  return (
    <Reveal delay={index * 0.04}>
      <div className={cn("card overflow-hidden transition-colors", open && "border-line-strong", finished && "bg-surface/60")}>
        <div className="flex items-center gap-3 p-4">
          <button
            onClick={() => update.mutate({ id: step.id, status: NEXT_STATUS[step.status] })}
            disabled={update.isPending}
            className={cn("focus-ring flex size-7 shrink-0 items-center justify-center rounded-full border transition-colors",
              step.status === "done" ? "border-ink bg-ink text-white" : "border-line-strong text-fg-2 hover:border-ink hover:text-fg")}
            aria-label={`Mark ${step.title} as ${NEXT_STATUS[step.status].replace("_", " ")}`}
            title={step.status === "todo" ? "Start" : step.status === "in_progress" ? "Mark done" : "Reset"}
          >
            <Icon className="size-3.5" />
          </button>
          <button onClick={() => setOpen((o) => !o)} aria-expanded={open} className="focus-ring flex min-w-0 flex-1 items-center justify-between gap-3 rounded text-left">
            <span className="min-w-0">
              <span className={cn("block truncate text-[15px] font-medium", finished && "text-fg-2 line-through decoration-line-strong")}>{step.title}</span>
              <span className="mt-0.5 flex flex-wrap gap-x-3 text-[12px] text-muted">
                <span>~{Math.round(step.est_hours)}h</span>
                {step.kind !== "skill" && <span className="capitalize">{step.kind}</span>}
                {step.is_prerequisite && <span>prerequisite</span>}
                {step.optional && <span>optional</span>}
                {step.status === "in_progress" && <span className="text-fg">in progress</span>}
                {step.status === "skipped" && <span>skipped — already known</span>}
              </span>
            </span>
            <ChevronDown className={cn("size-4 shrink-0 text-muted transition-transform", open && "rotate-180")} />
          </button>
        </div>
        <AnimatePresence initial={false}>
          {open && (
            <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} transition={{ duration: 0.28 }} className="overflow-hidden">
              <div className="grid gap-5 border-t border-line p-5 sm:grid-cols-2">
                {c.problem && <Block label="Problem">{c.problem}</Block>}
                {c.why_it_fits && <Block label="Why it fits you">{c.why_it_fits}</Block>}
                {!!c.learn?.length && (
                  <Block label={`Learn${c.focus ? ` · ${c.focus}` : ""}`}>
                    <ul className="space-y-1">{c.learn.slice(0, 3).map((r) => <li key={r.title}>→ <a href={r.url ?? "#"} target="_blank" rel="noreferrer" className="underline decoration-line-strong underline-offset-2 hover:decoration-black">{r.title}</a> <span className="text-muted">· {r.provider}</span></li>)}</ul>
                  </Block>
                )}
                {c.practice && <Block label="Practice">→ {c.practice}</Block>}
                {c.build && <Block label="Build">→ {c.build}</Block>}
                {c.architecture && <Block label="Architecture">{c.architecture.join(" → ")}</Block>}
                {c.prove && <Block label="Prove">→ {c.prove}</Block>}
                <div className="flex items-end gap-2 sm:col-span-2">
                  {step.status !== "done" && <Button size="sm" onClick={() => update.mutate({ id: step.id, status: "done" })} loading={update.isPending}><Check /> Mark complete</Button>}
                  {step.status === "todo" && step.kind === "skill" && <Button size="sm" variant="ghost" onClick={() => update.mutate({ id: step.id, status: "skipped" })}>I already know this</Button>}
                  <Link href="/app/learning" className="ml-auto text-[12px] text-muted hover:text-fg">All resources</Link>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Reveal>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><p className="eyebrow mb-1.5">{label}</p><div className="text-[14px] leading-relaxed text-fg-2">{children}</div></div>;
}

function AdjustDialog({ open, onOpenChange, hours }: { open: boolean; onOpenChange: (o: boolean) => void; hours: number }) {
  const [h, setH] = useState(hours);
  const [known, setKnown] = useState<string[]>([]);
  const [q, setQ] = useState("");
  const vocab = useVocab();
  const adjust = useAdjustRoadmap();
  const results = q.length > 1 ? (vocab.data?.all_skills ?? []).filter((s) => s.name.toLowerCase().includes(q.toLowerCase()) && !known.includes(s.id)).slice(0, 5) : [];
  const names = Object.fromEntries((vocab.data?.all_skills ?? []).map((s) => [s.id, s.name]));
  const apply = async () => {
    await adjust.mutateAsync({ hours_per_week: h !== hours ? h : undefined, known_skills: known });
    setKnown([]);
    onOpenChange(false);
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogTitle className="text-[20px] font-semibold tracking-tight">Adjust your roadmap</DialogTitle>
        <DialogDescription className="mt-1 text-[14px] text-fg-2">Your plan adapts — nothing you&apos;ve completed is lost.</DialogDescription>
        <div className="mt-6 space-y-6">
          <div>
            <Label htmlFor="adj-h">Hours available per week</Label>
            <div className="flex items-center gap-4">
              <input id="adj-h" type="range" min={1} max={40} value={h} onChange={(e) => setH(Number(e.target.value))} className="flex-1 accent-black" />
              <span className="w-16 text-right font-mono tabular-nums">{h} h</span>
            </div>
          </div>
          <div>
            <Label htmlFor="adj-k">I already know…</Label>
            <Input id="adj-k" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Docker" />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {results.map((s) => <button key={s.id} onClick={() => { setKnown([...known, s.id]); setQ(""); }} className="rounded-full border border-dashed border-line-strong px-2.5 py-1 text-[12px] hover:border-ink">+ {s.name}</button>)}
              {known.map((k) => <Badge key={k} tone="solid">{names[k]} <button onClick={() => setKnown(known.filter((x) => x !== k))} aria-label="remove">×</button></Badge>)}
            </div>
          </div>
          <Button className="w-full" onClick={apply} loading={adjust.isPending} disabled={h === hours && known.length === 0}>Apply changes</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
