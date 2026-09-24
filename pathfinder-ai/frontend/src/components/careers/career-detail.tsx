"use client";

import Link from "next/link";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { CareerGraph } from "@/components/careers/career-graph";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/motion";
import { Badge } from "@/components/ui/primitives";
import { SegmentBar } from "@/components/ui/segment-bar";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { useCareer } from "@/lib/queries";
import { pad2 } from "@/lib/utils";

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <Reveal className="grid gap-4 border-t border-line py-10 md:grid-cols-[220px_1fr]">
      <div className="flex gap-3 md:block">
        <p className="font-mono text-[12px] text-muted">{pad2(n)}</p>
        <h2 className="text-[15px] font-semibold md:mt-2">{title}</h2>
      </div>
      <div>{children}</div>
    </Reveal>
  );
}

const List = ({ items }: { items: string[] }) => (
  <ul className="space-y-2.5">{items.map((x) => <li key={x} className="flex gap-3 text-[16px] leading-relaxed text-fg-2"><span className="mt-[11px] size-1 shrink-0 rounded-full bg-fg" />{x}</li>)}</ul>
);

export function CareerDetailView({ id, publicView = false }: { id: string; publicView?: boolean }) {
  const { data: c, isLoading, error, refetch } = useCareer(id);
  if (isLoading) return <LoadingBlock rows={3} />;
  if (error || !c) return <ErrorState error={error} retry={refetch} />;
  const base = publicView ? "/explore" : "/app/careers";
  const personal = c.your_coverage !== null && !publicView;

  return (
    <article>
      <Link href={base} className="focus-ring mb-10 inline-flex items-center gap-1.5 rounded text-[13px] text-fg-2 hover:text-fg"><ArrowLeft className="size-3.5" /> All careers</Link>
      <header className="flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
        <div className="max-w-3xl">
          <Reveal><p className="eyebrow mb-4">{c.categories.join(" · ")}</p></Reveal>
          <Reveal delay={0.05}><h1 className="text-display font-semibold">{c.name}</h1></Reveal>
          <Reveal delay={0.1}><p className="mt-6 text-[19px] leading-relaxed text-fg-2">{c.summary}</p></Reveal>
        </div>
        <Reveal delay={0.15} className="flex shrink-0 flex-col items-start gap-3 md:items-end">
          {c.is_target ? (
            <Badge tone="solid"><Check className="size-3" /> Your current direction</Badge>
          ) : (
            <Button asChild size="lg"><Link href={publicView ? `/signup?next=/app/select/${c.id}` : `/app/select/${c.id}`}>Choose this direction <ArrowRight /></Link></Button>
          )}
          {!publicView && <Link href={`/app/careers/compare?ids=${c.id}`} className="text-[13px] text-fg-2 hover:text-fg">Compare with others</Link>}
        </Reveal>
      </header>

      {personal && (
        <Reveal delay={0.2} className="mt-12 grid gap-6 rounded-2xl border border-line bg-surface p-6 md:grid-cols-[1fr_2fr] md:items-center">
          <div>
            <p className="eyebrow mb-2">Your current coverage</p>
            <p className="text-[34px] font-semibold tabular-nums tracking-tight">{Math.round((c.your_coverage ?? 0) * 100)}%</p>
            <p className="text-[12px] text-muted">of this career&apos;s typical skill profile, from your stated skills and evidence</p>
          </div>
          <SegmentBar value={(c.your_coverage ?? 0) * 10} />
        </Reveal>
      )}

      <div className="mt-16">
        <Reveal><CareerGraph careerId={c.id} /></Reveal>
      </div>

      <div className="mt-16">
        <Section n={1} title="What they do"><p className="text-[17px] leading-relaxed text-fg">{c.what_they_do}</p></Section>
        <Section n={2} title="Typical responsibilities"><List items={c.responsibilities} /></Section>
        <Section n={3} title="Core skills">
          <div className="divide-y divide-line">
            {c.skills.map((s) => (
              <div key={s.skill_id} className="grid grid-cols-[1fr_auto] items-center gap-4 py-3 sm:grid-cols-[1fr_120px_140px]">
                <div className="flex items-center gap-2">
                  <span className="text-[15px] font-medium">{s.name}</span>
                  {s.importance === "core" && <Badge tone="solid">core</Badge>}
                  {s.importance === "useful" && <span className="text-[12px] text-muted">useful</span>}
                </div>
                <span className="text-[13px] text-fg-2">Typical: {s.target_label}</span>
                {s.your_label !== undefined && !publicView && (
                  <span className="hidden text-right text-[13px] text-muted sm:block">You: <span className={s.your_level! >= s.target_level ? "text-fg" : ""}>{s.your_label}</span></span>
                )}
              </div>
            ))}
          </div>
        </Section>
        <Section n={4} title="Useful technologies"><div className="flex flex-wrap gap-2">{c.technologies.map((t) => <Badge key={t}>{t}</Badge>)}</div></Section>
        <Section n={5} title="Common entry routes"><List items={c.entry_routes} /></Section>
        <Section n={6} title="Example projects">
          <List items={c.example_projects} />
          {c.project_templates.length > 0 && <p className="mt-4 text-[13px] text-muted">Detailed templates: {c.project_templates.map((p) => p.name).join(" · ")}</p>}
        </Section>
        {c.typical_learning_path.length > 0 && (
          <Section n={7} title="Typical learning path">
            <ol className="grid gap-3 sm:grid-cols-2">
              {c.typical_learning_path.map((p, i) => (
                <li key={p.name} className="card p-4">
                  <p className="font-mono text-[11px] text-muted">PHASE {pad2(i + 1)}</p>
                  <p className="mt-1 font-medium">{p.name}</p>
                  <p className="mt-1 text-[13px] text-fg-2">{p.skills.join(" · ")}</p>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-[13px] text-muted">Your personal roadmap skips what you already know.</p>
          </Section>
        )}
        <Section n={8} title="Related careers">
          <div className="grid gap-2 sm:grid-cols-2">
            {c.related.map((r) => (
              <Link key={r.id} href={`${base}/${r.id}`} className="card card-hover focus-ring p-4">
                <p className="font-medium">{r.name}</p>
                <p className="mt-1 line-clamp-2 text-[13px] text-fg-2">{r.summary}</p>
              </Link>
            ))}
          </div>
        </Section>
        <Section n={9} title="Who might enjoy this work"><List items={c.who_might_enjoy} /></Section>
        <Section n={10} title="Questions to explore before choosing it"><List items={c.questions_to_explore} /></Section>
        {c.certificates.length > 0 && (
          <Section n={11} title="Certificates sometimes useful">
            <p className="text-[15px] text-fg-2">{c.certificates.map((x) => x.name).join(" · ")}</p>
            <p className="mt-2 text-[13px] text-muted">Useful where they fill a real gap — practical evidence usually matters more.</p>
          </Section>
        )}
      </div>
      <p className="mt-6 border-t border-line pt-6 text-[13px] text-muted">{c.source_note}</p>
    </article>
  );
}
