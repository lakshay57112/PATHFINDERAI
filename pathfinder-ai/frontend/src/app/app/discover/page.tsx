"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Columns3, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Stagger, StaggerItem } from "@/components/ui/motion";
import { Badge, Card, Skeleton } from "@/components/ui/primitives";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { useDiscover } from "@/lib/queries";
import type { CareerMatch } from "@/lib/types";
import { cn, pad2 } from "@/lib/utils";

const TYPE_LABEL: Record<string, string> = { skill: "Skill", interest: "Interest", activity: "Enjoys", work_style: "Work style", project: "Project" };

export default function DiscoverPage() {
  const { data, isLoading, error, refetch, isFetching } = useDiscover();
  const [compare, setCompare] = useState<string[]>([]);
  const router = useRouter();
  const toggle = (id: string) => setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 4 ? c : [...c, id]));

  return (
    <div>
      <PageHeader
        eyebrow="Discover"
        title="Based on what you've told us, here are some paths worth exploring."
        description="These are possibilities, not a verdict. Each one shows why it appeared — so you can judge the fit yourself."
        actions={<Button variant="secondary" onClick={() => refetch()} loading={isFetching && !isLoading}>Refresh</Button>}
      />

      {isLoading ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">{["Profile Analyzer", "Career Discovery", "Career Research"].map((a) => <Badge key={a} tone="muted" className="animate-pulse">{a}…</Badge>)}</div>
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-48 w-full" />)}
        </div>
      ) : error || !data ? (
        <ErrorState error={error} retry={refetch} />
      ) : (
        <>
          <Stagger className="grid gap-4">
            {data.matches.map((m, i) => (
              <StaggerItem key={m.career_id}>
                <MatchCard m={m} index={i} selected={compare.includes(m.career_id)} onCompare={() => toggle(m.career_id)} related={data.research?.[m.career_id]?.related_careers} />
              </StaggerItem>
            ))}
          </Stagger>

          <div className="mt-12 flex flex-col gap-3 border-t border-line pt-6 text-[13px] text-muted md:flex-row md:items-center md:justify-between">
            <p className="flex items-center gap-2"><Info className="size-3.5" /> {data.principle}</p>
            <p className="font-mono">
              {data.trace.map((t) => t.agent.replace(" Agent", "")).join(" → ")} {data.ai_enriched ? "· AI-enriched" : ""}
            </p>
          </div>
          <p className="mt-4 text-[14px] text-fg-2">
            Not seeing something you expected? <Link href="/app/careers" className="text-fg underline underline-offset-4">Browse all careers</Link>.
          </p>
        </>
      )}

      {compare.length > 0 && (
        <motion.div initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
          className="fixed inset-x-4 bottom-24 z-30 mx-auto flex max-w-lg items-center justify-between gap-4 rounded-2xl border border-line bg-surface/95 p-3 pl-5 shadow-lift backdrop-blur lg:bottom-8 lg:left-[248px]">
          <p className="text-[14px]"><span className="font-semibold">{compare.length}</span> selected to compare <span className="text-muted">(up to 4)</span></p>
          <Button size="sm" disabled={compare.length < 2} onClick={() => router.push(`/app/careers/compare?ids=${compare.join(",")}`)}>
            <Columns3 /> Compare
          </Button>
        </motion.div>
      )}
    </div>
  );
}

function MatchCard({ m, index, selected, onCompare, related }: { m: CareerMatch; index: number; selected: boolean; onCompare: () => void; related?: { id: string; name: string }[] }) {
  return (
    <Card hover className={cn("p-6 md:p-8", selected && "border-ink")}>
      <div className="flex flex-col gap-6 md:flex-row md:justify-between">
        <div className="max-w-2xl">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[12px] text-muted">{pad2(index + 1)}</span>
            <Badge tone={m.fit_label === "Strong overlap" ? "solid" : "default"}>{m.fit_label}</Badge>
          </div>
          <h2 className="mt-4 text-[28px] font-semibold tracking-[-0.025em]">{m.name}</h2>
          <p className="mt-2 text-[16px] leading-relaxed text-fg-2">{m.summary}</p>
          {m.ai_explanation && <p className="mt-3 text-[15px] leading-relaxed text-fg">{m.ai_explanation}</p>}
        </div>
        <div className="flex shrink-0 gap-2 md:flex-col md:items-end">
          <Button asChild size="sm"><Link href={`/app/careers/${m.career_id}`}>Explore <ArrowRight /></Link></Button>
          <Button size="sm" variant={selected ? "primary" : "secondary"} onClick={onCompare} aria-pressed={selected}>
            {selected ? "Selected" : "Compare"}
          </Button>
        </div>
      </div>
      <div className="mt-7 grid gap-6 border-t border-line pt-6 md:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="eyebrow mb-3">Why it appeared</p>
          <p className="mb-3 text-[15px] font-medium">{m.why_summary}</p>
          <ul className="flex flex-wrap gap-1.5">
            {m.reasons.map((r, i) => (
              <li key={i} title={r.detail}>
                <Badge tone="muted"><span className="text-muted">{TYPE_LABEL[r.type] ?? r.type}:</span> {r.label}</Badge>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[12px] text-muted">All reasons come from your own profile.</p>
        </div>
        <div>
          {m.to_explore.length > 0 && (
            <>
              <p className="eyebrow mb-3">You&apos;d want to build</p>
              <p className="text-[14px] text-fg-2">{m.to_explore.join(" · ")}</p>
            </>
          )}
          {!!related?.length && (
            <>
              <p className="eyebrow mb-2 mt-5">Related paths</p>
              <p className="text-[14px] text-fg-2">
                {related.slice(0, 3).map((r, i) => (
                  <span key={r.id}>{i > 0 && " · "}<Link href={`/app/careers/${r.id}`} className="hover:text-fg hover:underline">{r.name}</Link></span>
                ))}
              </p>
            </>
          )}
        </div>
      </div>
    </Card>
  );
}
