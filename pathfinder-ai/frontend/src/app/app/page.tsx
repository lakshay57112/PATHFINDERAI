"use client";

import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/motion";
import { Card } from "@/components/ui/primitives";
import { ProgressLine } from "@/components/ui/segment-bar";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { useDashboard } from "@/lib/queries";
import { greeting, pad2 } from "@/lib/utils";

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useDashboard();
  if (isLoading) return <LoadingBlock rows={2} />;
  if (error || !data) return <ErrorState error={error} retry={refetch} />;
  const first = data.name?.split(" ")[0];

  return (
    <div>
      <Reveal>
        <p className="eyebrow mb-5">{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</p>
        <h1 className="text-title font-semibold">{greeting()}{first ? `, ${first}` : ""}.</h1>
        <p className="mt-3 text-[19px] text-fg-2">
          {data.target ? "Your career journey is moving forward." : "Let's find a direction worth exploring."}
        </p>
      </Reveal>

      {!data.target ? (
        <Reveal delay={0.1} className="mt-14">
          <Card className="flex flex-col items-start gap-5 p-8 md:p-10">
            <p className="eyebrow">Next</p>
            <p className="max-w-lg text-[24px] font-semibold leading-snug tracking-tight">See the paths that fit what you&apos;ve told us — each with the reasons it appeared.</p>
            <Button asChild size="lg"><Link href="/app/discover">Discover my paths <ArrowRight /></Link></Button>
          </Card>
        </Reveal>
      ) : (
        <>
          <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-2 xl:grid-cols-4">
            <Tile label="Current direction" delay={0}>
              <p className="text-[22px] font-semibold tracking-tight">{data.target.name}</p>
              <Link href={`/app/careers/${data.target.id}`} className="mt-auto inline-flex items-center gap-1 text-[13px] text-fg-2 hover:text-fg">Career details <ArrowUpRight className="size-3.5" /></Link>
            </Tile>
            <Tile label="Progress" delay={0.05}>
              {data.has_roadmap ? (
                <>
                  <p className="text-[40px] font-semibold leading-none tracking-tight tabular-nums">{Math.round((data.progress ?? 0) * 100)}%</p>
                  <ProgressLine value={data.progress ?? 0} className="mt-auto" />
                  <p className="text-[12px] text-muted">{data.remaining_label} remaining</p>
                </>
              ) : (
                <Button asChild size="sm" className="mt-auto w-fit"><Link href={`/app/select/${data.target.id}`}>Build my roadmap</Link></Button>
              )}
            </Tile>
            <Tile label="Next step" delay={0.1}>
              {data.next_step ? (
                <>
                  <p className="text-[17px] font-semibold leading-snug tracking-tight">{data.next_step.title}</p>
                  <p className="text-[13px] text-fg-2">{data.next_step.phase_name} · ~{Math.round(data.next_step.est_hours)}h</p>
                  <Link href="/app/roadmap" className="mt-auto inline-flex items-center gap-1 text-[13px] text-fg-2 hover:text-fg">Open roadmap <ArrowUpRight className="size-3.5" /></Link>
                </>
              ) : (
                <p className="text-fg-2">{data.has_roadmap ? "Everything required is done." : "Generate a roadmap to see it."}</p>
              )}
            </Tile>
            <Tile label="Recommended project" delay={0.15}>
              {data.recommended_project ? (
                <>
                  <p className="text-[17px] font-semibold leading-snug tracking-tight">{data.recommended_project.name}</p>
                  <p className="text-[13px] capitalize text-fg-2">{data.recommended_project.difficulty}</p>
                  <Link href="/app/projects" className="mt-auto inline-flex items-center gap-1 text-[13px] text-fg-2 hover:text-fg">Why it fits you <ArrowUpRight className="size-3.5" /></Link>
                </>
              ) : <p className="text-fg-2">—</p>}
            </Tile>
          </div>

          <div className="mt-16 grid gap-12 lg:grid-cols-[1.2fr_1fr]">
            <Reveal>
              <p className="eyebrow mb-6">Career insights</p>
              <div className="divide-y divide-line border-y border-line">
                {[
                  [data.insights?.skills_to_develop ?? 0, "skills to develop", "/app/gap"],
                  [data.insights?.projects_recommended ?? 0, "projects recommended", "/app/projects"],
                  [data.insights?.certificates_worth_exploring ?? 0, `certificate${data.insights?.certificates_worth_exploring === 1 ? "" : "s"} worth exploring`, "/app/certificates"],
                ].map(([n, label, href]) => (
                  <Link key={label as string} href={href as string} className="focus-ring group flex items-center justify-between py-5">
                    <span className="flex items-baseline gap-4">
                      <span className="w-10 text-[34px] font-semibold tabular-nums tracking-tight">{n as number}</span>
                      <span className="text-[17px] text-fg-2 group-hover:text-fg">{label as string}</span>
                    </span>
                    <ArrowRight className="size-4 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-fg" />
                  </Link>
                ))}
              </div>
              {data.readiness_next_step && (
                <p className="mt-8 max-w-lg text-[15px] leading-relaxed text-fg-2">
                  <span className="font-medium text-fg">Focus: </span>{data.readiness_next_step}
                </p>
              )}
            </Reveal>

            <Reveal delay={0.08}>
              <p className="eyebrow mb-6">Your phases</p>
              <ol className="space-y-4">
                {(data.phase_progress ?? []).map((p, i) => (
                  <li key={p.name} className="grid grid-cols-[28px_1fr_auto] items-center gap-3">
                    <span className="font-mono text-[12px] text-muted">{pad2(i + 1)}</span>
                    <div>
                      <p className="text-[14px] font-medium">{p.name}</p>
                      <ProgressLine value={p.status === "covered" ? 1 : p.progress} className="mt-2" />
                    </div>
                    <span className="w-16 text-right text-[12px] text-muted">
                      {p.status === "covered" ? "Covered" : p.status === "done" ? <Check className="ml-auto size-4 text-fg" /> : `${Math.round(p.progress * 100)}%`}
                    </span>
                  </li>
                ))}
              </ol>
              {!!data.recent_evidence?.length && (
                <div className="mt-10">
                  <p className="eyebrow mb-4">Recent evidence</p>
                  <ul className="space-y-2">
                    {data.recent_evidence.map((e) => (
                      <li key={e.id} className="flex items-center gap-3 text-[14px]">
                        <Check className="size-3.5 shrink-0 text-success" />
                        <span className="truncate">{e.title}</span>
                        <span className="ml-auto shrink-0 text-[12px] text-muted">{e.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Reveal>
          </div>
        </>
      )}
    </div>
  );
}

function Tile({ label, children, delay }: { label: string; children: React.ReactNode; delay: number }) {
  return (
    <Reveal delay={delay} className="flex flex-col gap-2 bg-surface p-6 md:min-h-[190px]">
      <p className="eyebrow mb-3">{label}</p>
      {children}
    </Reveal>
  );
}
