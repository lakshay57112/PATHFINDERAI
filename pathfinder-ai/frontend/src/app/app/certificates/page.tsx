"use client";

import { useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Info } from "lucide-react";
import { CertificateCard, CertificateForm, EvidenceList } from "@/components/evidence-forms";
import { Reveal } from "@/components/ui/motion";
import { Badge, Card } from "@/components/ui/primitives";
import { ErrorState, LoadingBlock, NeedsTarget, PageHeader, SectionTitle } from "@/components/ui/states";
import { ApiError, del } from "@/lib/api";
import { useProfile, useRecommendations } from "@/lib/queries";
import type { CertRec } from "@/lib/types";

const VERDICT: Record<CertRec["verdict"], { label: string; tone: "solid" | "default" | "muted" }> = {
  worth_exploring: { label: "Worth exploring", tone: "solid" },
  consider: { label: "Consider — project may be stronger", tone: "default" },
  project_first: { label: "Project first", tone: "muted" },
};

export default function CertificatesPage() {
  const profile = useProfile();
  const recs = useRecommendations();
  const qc = useQueryClient();
  const refresh = () => ["profile", "recommendations", "analysis", "dashboard", "gap"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));

  return (
    <div>
      <PageHeader eyebrow="Certificates" title="Certificates, weighed honestly."
        description="We look at what each certificate actually covers, compare it with your gaps and existing evidence, and only suggest one when it adds something a project wouldn't." />

      <section>
        <SectionTitle>Certificate intelligence</SectionTitle>
        {recs.isLoading ? <LoadingBlock rows={2} /> : recs.error instanceof ApiError && recs.error.code === "no_target_career" ? <NeedsTarget /> : recs.error || !recs.data ? <ErrorState error={recs.error} retry={recs.refetch} /> : (
          <>
            <p className="mb-6 flex max-w-2xl gap-2 text-[14px] text-fg-2"><Info className="mt-0.5 size-4 shrink-0" />{recs.data.certificates.principle}</p>
            <div className="grid gap-4 lg:grid-cols-2">
              {recs.data.certificates.recommendations.length === 0 && <p className="text-fg-2">No certificate stands out right now — projects will serve you better for your current gaps.</p>}
              {recs.data.certificates.recommendations.map((c, i) => (
                <Reveal key={c.id} delay={i * 0.06}>
                  <Card className="flex h-full flex-col p-6">
                    <div className="flex items-start justify-between gap-3">
                      <Badge tone={VERDICT[c.verdict].tone}>{VERDICT[c.verdict].label}</Badge>
                      <span className="text-[12px] capitalize text-muted">{c.type} · {c.level}</span>
                    </div>
                    <h3 className="mt-4 text-[19px] font-semibold leading-snug tracking-tight">{c.name}</h3>
                    <p className="text-[13px] text-muted">{c.provider}</p>
                    <p className="mt-4 text-[14.5px] leading-relaxed text-fg">{c.why}</p>
                    <dl className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-5 text-[13px]">
                      <div><dt className="eyebrow mb-1">Expected benefit</dt><dd className="text-fg-2">{c.expected_benefit}</dd></div>
                      <div><dt className="eyebrow mb-1">Difficulty · Time</dt><dd className="text-fg-2">{c.difficulty} · {c.time_required}</dd></div>
                      {c.evidence.already_demonstrated.length > 0 && <div className="col-span-2"><dt className="eyebrow mb-1">Already shown by your profile</dt><dd className="text-fg-2">{c.evidence.already_demonstrated.join(", ")}</dd></div>}
                    </dl>
                    {c.notes && <p className="mt-4 text-[12.5px] text-muted">{c.notes}</p>}
                    {c.url && <a href={c.url} target="_blank" rel="noreferrer" className="mt-auto inline-flex items-center gap-1 pt-5 text-[13px] text-fg-2 hover:text-fg">Official page (check current requirements) <ArrowUpRight className="size-3.5" /></a>}
                  </Card>
                </Reveal>
              ))}
            </div>
            {recs.data.certificates.existing.length > 0 && (
              <div className="mt-10">
                <p className="eyebrow mb-4">What your current certificates demonstrate</p>
                <div className="divide-y divide-line border-y border-line">
                  {recs.data.certificates.existing.map((e) => (
                    <div key={e.name} className="grid gap-2 py-4 md:grid-cols-[1fr_1.4fr]">
                      <p className="font-medium">{e.name}{e.matched_catalog && e.matched_catalog !== e.name && <span className="block text-[12px] font-normal text-muted">≈ {e.matched_catalog}</span>}</p>
                      <p className="text-[14px] text-fg-2">
                        {e.demonstrates.join(", ") || "—"}
                        {e.relevant_to_target.length > 0 && <span className="block text-[12px] text-muted">Relevant to your target: {e.relevant_to_target.join(", ")}</span>}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </section>

      <section className="mt-20">
        <SectionTitle>Your certificates</SectionTitle>
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <CertificateForm onAdded={refresh} />
          <EvidenceList>
            {(profile.data?.certificates ?? []).map((c) => (
              <CertificateCard key={c.id} c={c} onDelete={async () => { await del(`/certificates/${c.id}`).catch(() => {}); refresh(); }} />
            ))}
          </EvidenceList>
        </div>
      </section>
    </div>
  );
}
