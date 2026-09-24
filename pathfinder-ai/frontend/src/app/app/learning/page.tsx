"use client";

import { Check } from "lucide-react";
import { Reveal } from "@/components/ui/motion";
import { Badge } from "@/components/ui/primitives";
import { EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/ui/states";
import { ApiError } from "@/lib/api";
import { useLearning } from "@/lib/queries";
import type { LearningItem } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function LearningPage() {
  const { data, isLoading, error, refetch } = useLearning();
  if (isLoading) return <LoadingBlock rows={4} />;
  if (error instanceof ApiError && error.status === 404) return <EmptyState title="No learning plan yet" description="Generate a roadmap and your learning plan appears here." action={{ href: "/app/discover", label: "Choose a direction" }} />;
  if (error || !data) return <ErrorState error={error} retry={refetch} />;

  const byPhase = (data.items as LearningItem[]).reduce<Record<string, LearningItem[]>>((acc, it) => {
    (acc[it.phase ?? "Other"] ||= []).push(it);
    return acc;
  }, {});

  return (
    <div>
      <PageHeader eyebrow="Learning" title="Learn → Practice → Build → Prove." description={data.principle} />
      <div className="space-y-16">
        {Object.entries(byPhase).map(([phase, items]) => (
          <section key={phase}>
            <p className="eyebrow mb-5">{phase}</p>
            <div className="space-y-4">
              {items.map((it, i) => (
                <Reveal key={it.skill_id} delay={i * 0.04}>
                  <article className={cn("card p-6", it.status === "done" && "opacity-70")}>
                    <div className="flex flex-wrap items-baseline justify-between gap-3">
                      <h3 className="flex items-center gap-2 text-[20px] font-semibold tracking-tight">
                        {it.status === "done" && <Check className="size-4" />}{it.name}
                      </h3>
                      <div className="flex items-center gap-2">
                        <Badge tone="muted">{it.focus}</Badge>
                        <span className="font-mono text-[12px] text-muted">~{Math.round(it.estimated_hours)}h</span>
                      </div>
                    </div>
                    <div className="mt-6 grid gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-4">
                      <Col label="Learn">
                        <ul className="space-y-2">
                          {it.learn.slice(0, 3).map((r) => (
                            <li key={r.title}>
                              <a href={r.url ?? "#"} target="_blank" rel="noreferrer" className="font-medium text-fg underline decoration-line-strong underline-offset-2 hover:decoration-black">{r.title}</a>
                              <span className="block text-[12px] text-muted">{r.provider}{r.type ? ` · ${r.type}` : ""}</span>
                            </li>
                          ))}
                        </ul>
                      </Col>
                      <Col label="Practice">{it.practice}</Col>
                      <Col label="Build">{it.build}</Col>
                      <Col label="Prove">{it.prove}</Col>
                    </div>
                  </article>
                </Reveal>
              ))}
            </div>
          </section>
        ))}
      </div>
      <p className="mt-12 text-[13px] text-muted">Resources are well-known public materials curated in PathFinder&apos;s knowledge base. Links open the provider&apos;s site.</p>
    </div>
  );
}

function Col({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="bg-surface p-4"><p className="eyebrow mb-2">{label}</p><div className="text-[13.5px] leading-relaxed text-fg-2">{children}</div></div>;
}
