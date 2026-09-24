"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { ArrowRight, PencilLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/motion";
import { Badge, Card } from "@/components/ui/primitives";
import { SegmentBar } from "@/components/ui/segment-bar";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { useAnalysis } from "@/lib/queries";

function ProfileInner() {
  const isNew = useSearchParams().get("new") === "1";
  const { data, isLoading, error, refetch } = useAnalysis();
  if (isLoading) return <LoadingBlock rows={2} />;
  if (error || !data) return <ErrorState error={error} retry={refetch} />;

  return (
    <div>
      <header className="mb-14 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <Reveal><p className="eyebrow mb-4">Your career profile</p></Reveal>
          <Reveal delay={0.05}><h1 className="text-display font-semibold">{data.name || "You"}</h1></Reveal>
          <Reveal delay={0.1}><p className="mt-6 max-w-2xl text-[18px] leading-relaxed text-fg-2">{data.summary}</p></Reveal>
        </div>
        <Reveal delay={0.15} className="flex gap-2">
          <Button asChild variant="secondary"><Link href="/onboarding"><PencilLine /> Edit profile</Link></Button>
          {!isNew && <Button asChild><Link href="/app/discover">Explore paths <ArrowRight /></Link></Button>}
        </Reveal>
      </header>

      <div className="grid gap-14 lg:grid-cols-[1.25fr_1fr]">
        <section>
          <div className="space-y-6">
            {data.domains.map((d, i) => (
              <Reveal key={d.domain} delay={i * 0.04}>
                <div className="grid grid-cols-[120px_1fr] items-center gap-5 sm:grid-cols-[150px_1fr_40px]">
                  <div>
                    <p className="text-[15px] font-medium">{d.label}</p>
                  </div>
                  <SegmentBar value={d.score} delay={0.1 + i * 0.05} />
                  <span className="hidden text-right font-mono text-[12px] tabular-nums text-muted sm:block">{d.score.toFixed(1)}</span>
                  {d.reasons.length > 0 && (
                    <p className="col-span-2 -mt-3 text-[12.5px] text-muted sm:col-span-3 sm:col-start-2">{d.reasons.slice(0, 3).join(" · ")}</p>
                  )}
                </div>
              </Reveal>
            ))}
          </div>
          <p className="mt-8 border-t border-line pt-4 text-[13px] text-muted">{data.disclaimer}</p>
        </section>

        <aside className="space-y-10">
          <Block title="Strong interests">{data.strong_interests.join(" · ") || "—"}</Block>
          <Block title="Current strengths">
            {data.current_strengths.length ? data.current_strengths.map((s) => s.name).join(" · ") : "Add skills to see your strengths."}
          </Block>
          <Block title="Work preferences">{data.work_preferences.join(" · ") || "—"}</Block>
          {data.developing_skills.length > 0 && (
            <div>
              <p className="eyebrow mb-3">Developing</p>
              <div className="flex flex-wrap gap-1.5">{data.developing_skills.map((s) => <Badge key={s.skill_id} tone="muted">{s.name}</Badge>)}</div>
            </div>
          )}
          {data.unsure_skills.length > 0 && (
            <p className="text-[13px] text-fg-2">You weren&apos;t sure about {data.unsure_skills.join(", ")} — that&apos;s fine. We&apos;ll treat them as areas to explore.</p>
          )}
          <div className="grid grid-cols-3 gap-px overflow-hidden rounded-xl border border-line bg-line">
            {[["Skills", data.stats.skills], ["Projects", data.stats.projects], ["Certificates", data.stats.certificates]].map(([l, n]) => (
              <div key={l as string} className="bg-surface p-4">
                <p className="text-[24px] font-semibold tabular-nums tracking-tight">{n}</p>
                <p className="text-[12px] text-muted">{l}</p>
              </div>
            ))}
          </div>
        </aside>
      </div>

      {isNew && (
        <Reveal delay={0.3} className="mt-20">
          <Card className="flex flex-col items-start justify-between gap-6 p-8 md:flex-row md:items-center md:p-10">
            <div>
              <p className="eyebrow mb-3">Next</p>
              <p className="text-[24px] font-semibold tracking-tight">Here are some paths worth exploring.</p>
              <p className="mt-1 text-fg-2">Based on everything you&apos;ve told us — with the reasons each one appeared.</p>
            </div>
            <Button asChild size="lg"><Link href="/app/discover">See my paths <ArrowRight /></Link></Button>
          </Card>
        </Reveal>
      )}
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Reveal>
      <p className="eyebrow mb-3">{title}</p>
      <p className="text-[19px] font-medium leading-snug tracking-tight">{children}</p>
    </Reveal>
  );
}

export default function ProfilePage() {
  return <Suspense><ProfileInner /></Suspense>;
}
