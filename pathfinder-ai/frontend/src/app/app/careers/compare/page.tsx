"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { Input, Skeleton } from "@/components/ui/primitives";
import { ErrorState, PageHeader } from "@/components/ui/states";
import { post } from "@/lib/api";
import { useCareers } from "@/lib/queries";
import { cn } from "@/lib/utils";

type Col = {
  career_id: string; name: string; skill_focus: string; typical_outputs: string; learning_areas: string[]; technologies: string[];
  dimensions: Record<string, { level: number; label: string }>; your_coverage?: number; you_already_have?: string[];
};

function Emphasis({ level, label }: { level: number; label: string }) {
  return (
    <div>
      <div className="flex gap-1" aria-hidden>{[1, 2, 3].map((i) => <span key={i} className={cn("h-1.5 w-6 rounded-full", i <= level ? "bg-ink" : "bg-[#e6e6e6]")} />)}</div>
      <p className="mt-1.5 text-[13px] text-fg-2">{label}</p>
    </div>
  );
}

function CompareInner() {
  const params = useSearchParams();
  const router = useRouter();
  const ids = useMemo(() => (params.get("ids") ?? "").split(",").filter(Boolean).slice(0, 4), [params]);
  const [q, setQ] = useState("");
  const all = useCareers(undefined, q.length > 1 ? q : undefined);
  const setIds = (next: string[]) => router.replace(`/app/careers/compare?ids=${next.join(",")}`, { scroll: false });
  const cmp = useQuery({
    queryKey: ["compare", ids],
    queryFn: () => post<{ careers: Col[]; rows: { key: string; label: string }[]; shared_skills: string[]; note: string }>("/career/compare", { career_ids: ids }),
    enabled: ids.length >= 2,
  });

  return (
    <div>
      <PageHeader eyebrow="Compare" title="Compare careers side by side." description="Neutral, factual differences in skill focus and typical work — plus how much of each you already cover." />
      <div className="mb-8 flex flex-wrap items-center gap-2">
        {ids.map((id) => (
          <span key={id} className="inline-flex items-center gap-1.5 rounded-full border border-ink bg-ink py-1.5 pl-3.5 pr-2 text-[13px] text-white">
            {cmp.data?.careers.find((c) => c.career_id === id)?.name ?? id}
            <button onClick={() => setIds(ids.filter((x) => x !== id))} className="rounded-full p-0.5 hover:bg-white/15" aria-label="Remove"><X className="size-3" /></button>
          </span>
        ))}
        {ids.length < 4 && (
          <div className="relative">
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Add a career…" className="h-9 w-56 rounded-full text-[13px]" />
            {q.length > 1 && (
              <div className="absolute z-20 mt-1 w-72 overflow-hidden rounded-xl border border-line bg-surface shadow-lift">
                {all.data?.items.filter((c) => !ids.includes(c.id)).slice(0, 6).map((c) => (
                  <button key={c.id} onClick={() => { setIds([...ids, c.id]); setQ(""); }} className="flex w-full items-center gap-2 px-3 py-2 text-left text-[14px] hover:bg-surface-2">
                    <Plus className="size-3.5 text-muted" /> {c.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {ids.length < 2 ? (
        <p className="text-fg-2">Add at least two careers to compare. Tip: select them from <Link href="/app/discover" className="text-fg underline underline-offset-4">Discover</Link>.</p>
      ) : cmp.isLoading ? (
        <Skeleton className="h-[520px]" />
      ) : cmp.error || !cmp.data ? (
        <ErrorState error={cmp.error} retry={cmp.refetch} />
      ) : (
        <>
          <div className="overflow-x-auto rounded-2xl border border-line bg-surface">
            <table className="w-full min-w-[720px] border-collapse text-left">
              <thead>
                <tr className="border-b border-line">
                  <th className="w-44 p-5" />
                  {cmp.data.careers.map((c) => (
                    <th key={c.career_id} className="p-5 align-bottom">
                      <Link href={`/app/careers/${c.career_id}`} className="text-[17px] font-semibold tracking-tight hover:underline">{c.name}</Link>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line text-[14px]">
                <Row label="Skill focus">{cmp.data.careers.map((c) => <td key={c.career_id} className="p-5 text-fg">{c.skill_focus}</td>)}</Row>
                {cmp.data.rows.map((r) => (
                  <Row key={r.key} label={r.label}>{cmp.data!.careers.map((c) => <td key={c.career_id} className="p-5"><Emphasis {...c.dimensions[r.key]} /></td>)}</Row>
                ))}
                <Row label="Typical outputs">{cmp.data.careers.map((c) => <td key={c.career_id} className="p-5 text-fg-2">{c.typical_outputs}</td>)}</Row>
                <Row label="Learning areas">{cmp.data.careers.map((c) => <td key={c.career_id} className="p-5 text-fg-2">{c.learning_areas.join(", ")}</td>)}</Row>
                <Row label="Technologies">{cmp.data.careers.map((c) => <td key={c.career_id} className="p-5 text-fg-2">{c.technologies.join(", ")}</td>)}</Row>
                {cmp.data.careers[0]?.your_coverage !== undefined && (
                  <Row label="You already cover">
                    {cmp.data.careers.map((c) => (
                      <td key={c.career_id} className="p-5">
                        <p className="text-[20px] font-semibold tabular-nums">{Math.round((c.your_coverage ?? 0) * 100)}%</p>
                        <p className="mt-1 text-[12px] text-muted">{c.you_already_have?.join(", ") || "—"}</p>
                      </td>
                    ))}
                  </Row>
                )}
              </tbody>
            </table>
          </div>
          {cmp.data.shared_skills.length > 0 && (
            <p className="mt-6 text-[14px] text-fg-2"><span className="font-medium text-fg">Shared foundation: </span>{cmp.data.shared_skills.join(", ")} — learning these keeps several doors open.</p>
          )}
          <p className="mt-3 text-[13px] text-muted">{cmp.data.note}</p>
        </>
      )}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return <tr className="align-top"><th scope="row" className="p-5 text-[12px] font-medium uppercase tracking-wider text-muted">{label}</th>{children}</tr>;
}

export default function ComparePage() {
  return <Suspense><CompareInner /></Suspense>;
}
