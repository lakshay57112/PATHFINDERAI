"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { EvidenceList, ProjectCard, ProjectForm } from "@/components/evidence-forms";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/ui/motion";
import { Badge, Card } from "@/components/ui/primitives";
import { ErrorState, LoadingBlock, NeedsTarget, PageHeader, SectionTitle } from "@/components/ui/states";
import { ApiError, del, post } from "@/lib/api";
import { useProfile, useRecommendations } from "@/lib/queries";
import type { ProjectRec } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ProjectsPage() {
  const recs = useRecommendations();
  const profile = useProfile();
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const refresh = () => { qc.invalidateQueries({ queryKey: ["profile"] }); qc.invalidateQueries({ queryKey: ["analysis"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); };

  const start = async (p: ProjectRec) => {
    try {
      await post("/projects", { name: p.name, description: `${p.problem}\n\nPlanned architecture: ${p.architecture.join(" → ")}`, technologies: p.technologies, status: "planned" });
      toast.success("Added to your projects as planned. Mark it complete when it's built.");
      refresh();
    } catch (e) { toast.error(e instanceof Error ? e.message : "Couldn't add project."); }
  };

  return (
    <div>
      <PageHeader eyebrow="Projects" title="Build evidence, not just knowledge."
        description="Projects chosen to close your specific gaps, reuse your strengths and connect to what you care about." />

      {recs.isLoading ? <LoadingBlock rows={3} /> : recs.error instanceof ApiError && recs.error.code === "no_target_career" ? <NeedsTarget /> : recs.error || !recs.data ? <ErrorState error={recs.error} retry={recs.refetch} /> : (
        <section>
          <SectionTitle hint={`For ${recs.data.career_name}`}>Recommended for you</SectionTitle>
          <div className="space-y-4">
            {recs.data.projects.projects.map((p, i) => <ProjectRecCard key={p.id} p={p} index={i} onStart={() => start(p)} />)}
          </div>
        </section>
      )}

      <section className="mt-20">
        <SectionTitle hint={<Button size="sm" variant="secondary" onClick={() => setAdding((a) => !a)}><Plus /> Add project</Button>}>Your projects</SectionTitle>
        {adding && <div className="mb-4"><ProjectForm onAdded={() => { refresh(); setAdding(false); toast.success("Project analysed and added."); }} /></div>}
        {profile.data && (
          <EvidenceList>
            {profile.data.projects.length === 0 ? <p className="text-fg-2">No projects yet — add one to see which skills it demonstrates.</p> :
              profile.data.projects.map((p) => (
                <ProjectCard key={p.id} p={p} onDelete={async () => { await del(`/projects/${p.id}`).catch(() => {}); refresh(); }} />
              ))}
          </EvidenceList>
        )}
      </section>
    </div>
  );
}

function ProjectRecCard({ p, index, onStart }: { p: ProjectRec; index: number; onStart: () => void }) {
  return (
    <Reveal delay={index * 0.06}>
      <Card className={cn("p-6 md:p-8", p.suggested_start && "border-ink")}>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={p.difficulty === "advanced" ? "solid" : "default"} className="capitalize">{p.difficulty}</Badge>
              {p.suggested_start && <Badge tone="muted">Suggested starting point</Badge>}
              <span className="text-[13px] text-muted">{p.estimated_time}</span>
            </div>
            <h3 className="mt-4 text-[24px] font-semibold tracking-tight">{p.name}</h3>
            <p className="mt-2 text-[15px] leading-relaxed text-fg-2">{p.problem}</p>
          </div>
          <Button size="sm" variant="secondary" onClick={onStart} className="shrink-0">Start this project</Button>
        </div>
        <div className="mt-6 grid gap-6 border-t border-line pt-6 md:grid-cols-3">
          <Info label="Why it fits you">{p.why_it_fits}</Info>
          <Info label="Skills learned">{p.skills_learned.join(" · ")}</Info>
          <Info label="Technologies">{p.technologies.join(" · ")}</Info>
          <Info label="Architecture" className="md:col-span-2">
            <div className="flex flex-wrap items-center gap-1.5">
              {p.architecture.map((a, i) => (
                <span key={a} className="flex items-center gap-1.5">
                  <span className="rounded-md border border-line bg-surface-2 px-2 py-1 text-[12.5px] text-fg">{a}</span>
                  {i < p.architecture.length - 1 && <span className="text-muted">→</span>}
                </span>
              ))}
            </div>
          </Info>
          <Info label="Expected output">{p.expected_output}</Info>
          <Info label="Portfolio value" className="md:col-span-3">{p.portfolio_value}</Info>
        </div>
      </Card>
    </Reveal>
  );
}

function Info({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return <div className={className}><p className="eyebrow mb-2">{label}</p><div className="text-[14px] leading-relaxed text-fg-2">{children}</div></div>;
}
