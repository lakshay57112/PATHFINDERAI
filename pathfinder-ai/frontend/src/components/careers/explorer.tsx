"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useDeferredValue, useState } from "react";
import { ArrowUpRight, Search } from "lucide-react";
import { Chip } from "@/components/onboarding/choice";
import { Stagger, StaggerItem } from "@/components/ui/motion";
import { Input, Skeleton } from "@/components/ui/primitives";
import { useCareers, useCategories } from "@/lib/queries";

export function CareerExplorer({ base }: { base: "/app/careers" | "/explore" }) {
  const params = useSearchParams();
  const router = useRouter();
  const category = params.get("category") ?? undefined;
  const [q, setQ] = useState("");
  const dq = useDeferredValue(q);
  const cats = useCategories();
  const careers = useCareers(category, dq.trim().length > 1 ? dq.trim() : undefined);

  const setCat = (c?: string) => router.replace(c ? `${base}?category=${c}` : base, { scroll: false });

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4">
        <div className="relative max-w-md">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search careers or skills — e.g. “SQL”, “design”" className="pl-10" aria-label="Search careers" />
        </div>
        <div className="flex flex-wrap gap-2">
          <Chip size="sm" label="All" selected={!category} onClick={() => setCat()} />
          {cats.data?.map((c) => <Chip key={c.id} size="sm" label={`${c.label} ${c.count}`} selected={category === c.id} onClick={() => setCat(c.id)} />)}
        </div>
      </div>
      {careers.isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 9 }).map((_, i) => <Skeleton key={i} className="h-40" />)}</div>
      ) : (
        <>
          <p className="mb-4 text-[13px] text-muted">{careers.data?.total ?? 0} careers</p>
          <Stagger key={`${category}-${dq}`} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" gap={0.025}>
            {careers.data?.items.map((c) => (
              <StaggerItem key={c.id}>
                <Link href={`${base}/${c.id}`} className="card card-hover focus-ring group flex h-full flex-col p-5">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-[17px] font-semibold tracking-tight">{c.name}</h3>
                    <ArrowUpRight className="size-4 shrink-0 text-muted transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-fg" />
                  </div>
                  <p className="mt-2 line-clamp-2 text-[14px] leading-relaxed text-fg-2">{c.summary}</p>
                  <p className="mt-auto pt-5 font-mono text-[11px] uppercase tracking-wider text-muted">{c.skill_focus}</p>
                </Link>
              </StaggerItem>
            ))}
          </Stagger>
        </>
      )}
    </div>
  );
}
