"use client";

import Link from "next/link";
import { ArrowRight, Check, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/motion";
import { Badge, Card } from "@/components/ui/primitives";
import { SegmentBar } from "@/components/ui/segment-bar";
import { EmptyState, ErrorState, LoadingBlock, SectionTitle } from "@/components/ui/states";
import { useProgress } from "@/lib/queries";

export default function ProgressPage() {
  const { data, isLoading, error, refetch } = useProgress();
  if (isLoading) return <LoadingBlock rows={3} />;
  if (error || !data) return <ErrorState error={error} retry={refetch} />;
  if (!data.has_roadmap) return <EmptyState title="Your journey starts with a direction" description="Pick a career and generate a roadmap to start tracking progress." action={{ href: "/app/discover", label: "Discover my paths" }} />;
  const r = data.readiness!;
  const overall = data.overall ?? 0;

  return (
    <div>
      <Reveal><p className="eyebrow mb-6">Your journey · {data.career_name}</p></Reveal>
      <Reveal delay={0.05}>
        <div className="flex items-end gap-6">
          <p className="text-display font-semibold tabular-nums">{Math.round(overall * 100)}%</p>
          <p className="mb-3 text-[14px] text-fg-2">{data.remaining_label} remaining</p>
        </div>
        <SegmentBar value={overall * 18} segments={18} className="mt-6 max-w-2xl" />
        <p className="mt-3 text-[12px] text-muted">{data.overall_basis}</p>
      </Reveal>

      <Reveal delay={0.1} className="mt-14 grid grid-cols-3 gap-px overflow-hidden rounded-2xl border border-line bg-line">
        {[["Skills", data.skills!], ["Projects", data.projects!], ["Roadmap phases", data.phases!]].map(([label, v]) => {
          const x = v as { done: number; total: number };
          return (
            <div key={label as string} className="bg-surface p-6">
              <p className="eyebrow mb-3">{label as string}</p>
              <p className="text-[34px] font-semibold tabular-nums tracking-tight">{x.done}<span className="text-muted"> / {x.total}</span></p>
            </div>
          );
        })}
      </Reveal>

      {data.next_step && (
        <Reveal className="mt-8">
          <Card className="flex flex-col justify-between gap-4 p-6 md:flex-row md:items-center">
            <div><p className="eyebrow mb-2">Next step</p><p className="text-[18px] font-semibold tracking-tight">{data.next_step.title}</p><p className="text-[13px] text-fg-2">{data.next_step.phase_name}</p></div>
            <Button asChild><Link href="/app/roadmap">Continue <ArrowRight /></Link></Button>
          </Card>
        </Reveal>
      )}

      <section className="mt-20">
        <SectionTitle hint="Not a percentage — evidence">Career readiness</SectionTitle>
        <div className="grid gap-4 md:grid-cols-3">
          {([["Strong", r.buckets.strong], ["Developing", r.buckets.developing], ["Limited evidence", r.buckets.limited]] as const).map(([label, items], i) => (
            <Reveal key={label} delay={i * 0.06}>
              <Card className="h-full p-6">
                <p className="eyebrow mb-4">{label}</p>
                <ul className="space-y-2.5">
                  {items.length === 0 && <li className="text-[14px] text-muted">—</li>}
                  {items.map((e) => (
                    <li key={e.skill_id} className="flex items-baseline justify-between gap-3">
                      <span className="text-[15px] font-medium">{e.name}</span>
                      <span className="shrink-0 text-[11.5px] text-muted">{e.evidence}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </Reveal>
          ))}
        </div>
        <Reveal className="mt-6 border-l-2 border-ink pl-4">
          <p className="text-[17px] font-medium leading-snug">{r.next_step}</p>
          {r.self_reported_note && <p className="mt-2 text-[14px] text-fg-2">{r.self_reported_note}</p>}
          <p className="mt-2 text-[12px] text-muted">{r.principle}</p>
        </Reveal>
      </section>

      <section className="mt-20">
        <SectionTitle hint={`${data.evidence.length} items`}>Evidence</SectionTitle>
        {data.evidence.length === 0 ? <p className="text-fg-2">Complete roadmap steps, add projects or pass quizzes to build evidence.</p> : (
          <ul className="divide-y divide-line border-y border-line">
            {data.evidence.map((e) => (
              <li key={e.id} className="grid grid-cols-[20px_1fr_auto] items-start gap-3 py-4">
                <Check className="mt-1 size-4 text-success" />
                <div className="min-w-0">
                  <p className="text-[15px] font-medium">{e.title}</p>
                  <p className="text-[13px] text-fg-2">{[e.detail, e.skills.join(", ")].filter(Boolean).join(" · ")}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone="muted">✓ {e.label}</Badge>
                  {e.url && <a href={e.url} target="_blank" rel="noreferrer" className="text-muted hover:text-fg" aria-label="Open evidence"><ExternalLink className="size-3.5" /></a>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
