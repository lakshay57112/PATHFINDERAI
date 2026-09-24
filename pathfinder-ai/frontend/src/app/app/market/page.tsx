"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Check, ClipboardPaste, Database } from "lucide-react";
import { Chip } from "@/components/onboarding/choice";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Reveal } from "@/components/ui/motion";
import { Badge, Card, Input, Label, Skeleton, Textarea } from "@/components/ui/primitives";
import { ErrorState, PageHeader, SectionTitle } from "@/components/ui/states";
import { get, post } from "@/lib/api";
import { useCareers, useProfile } from "@/lib/queries";
import { cn } from "@/lib/utils";

type Row = { skill_id: string; name: string; share: number; count: number; you_have: boolean; your_level: string };
type Analysis = {
  career_name: string; sample_size: number; period: { from: string; to: string } | null; headline: string | null; insufficient: boolean;
  sources: { source: string; count: number; synthetic: boolean; yours: boolean }[]; synthetic_only: boolean;
  skills: Row[]; technologies: Row[]; experience: { postings_with_requirement?: number; median_min_years?: number | null; distribution?: Record<string, number> };
  education: { label: string; share: number }[]; certifications: { name: string; share: number }[]; responsibilities: string[]; disclaimers: string[];
};

const fmt = (d: string) => new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

export default function MarketPage() {
  const profile = useProfile();
  const careers = useCareers();
  const options = useQuery({ queryKey: ["market-options"], queryFn: () => get<{ countries: string[]; cities: string[]; industries: string[] }>("/market/options") });
  const [f, setF] = useState({ career_id: "", country: "", city: "", industry: "", remote: "any", include_synthetic: true });
  const [pasteOpen, setPasteOpen] = useState(false);

  useEffect(() => {
    if (!f.career_id && profile.data?.target_career_id) setF((x) => ({ ...x, career_id: profile.data!.target_career_id! }));
  }, [profile.data, f.career_id]);

  const analysis = useQuery({
    queryKey: ["market", f],
    enabled: !!f.career_id,
    queryFn: () => post<Analysis>("/market/analyze", {
      career_id: f.career_id, country: f.country || null, city: f.city || null, industry: f.industry || null,
      remote: f.remote === "any" ? null : f.remote === "remote", include_synthetic: f.include_synthetic,
    }),
  });
  const d = analysis.data;

  return (
    <div>
      <PageHeader eyebrow="Job market intelligence" title="What employers ask for."
        description="Skills, technologies and requirements extracted from job descriptions — always with the data source and time period."
        actions={<Button variant="secondary" onClick={() => setPasteOpen(true)}><ClipboardPaste /> Analyse your own job posts</Button>} />

      <Card className="mb-10 grid gap-4 p-5 md:grid-cols-5">
        <Select label="Career" value={f.career_id} onChange={(v) => setF({ ...f, career_id: v })} options={(careers.data?.items ?? []).map((c) => [c.id, c.name])} />
        <Select label="Country" value={f.country} onChange={(v) => setF({ ...f, country: v, city: "" })} options={[["", "All"], ...(options.data?.countries ?? []).map((c) => [c, c] as [string, string])]} />
        <Select label="City" value={f.city} onChange={(v) => setF({ ...f, city: v })} options={[["", "All"], ...(options.data?.cities ?? []).map((c) => [c, c] as [string, string])]} />
        <Select label="Industry" value={f.industry} onChange={(v) => setF({ ...f, industry: v })} options={[["", "All"], ...(options.data?.industries ?? []).map((c) => [c, c] as [string, string])]} />
        <div>
          <Label>Work mode</Label>
          <div className="flex gap-1.5">{["any", "remote", "onsite"].map((m) => <Chip key={m} size="sm" label={m === "any" ? "Any" : m === "remote" ? "Remote" : "On-site"} selected={f.remote === m} onClick={() => setF({ ...f, remote: m })} />)}</div>
        </div>
        <label className="flex items-center gap-2 text-[13px] text-fg-2 md:col-span-5">
          <input type="checkbox" checked={f.include_synthetic} onChange={(e) => setF({ ...f, include_synthetic: e.target.checked })} className="accent-black" />
          Include PathFinder&apos;s synthetic demo sample
        </label>
      </Card>

      {!f.career_id ? <p className="text-fg-2">Choose a career to analyse.</p> : analysis.isLoading ? <Skeleton className="h-96" /> : analysis.error || !d ? <ErrorState error={analysis.error} retry={analysis.refetch} /> : (
        <div>
          <Reveal className="mb-10 rounded-xl border border-line bg-surface p-5">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[14px]">
              <span className="flex items-center gap-2 font-medium"><Database className="size-4" /> {d.sample_size} job descriptions</span>
              {d.period && <span className="text-fg-2">{fmt(d.period.from)} – {fmt(d.period.to)}</span>}
            </div>
            <ul className="mt-3 space-y-1 text-[13px] text-fg-2">
              {d.sources.map((s) => (
                <li key={s.source} className="flex flex-wrap items-center gap-2">
                  Source: <span className="text-fg">{s.source}</span> · {s.count}
                  {s.synthetic && <Badge tone="warning">Synthetic</Badge>}
                  {s.yours && <Badge tone="muted">Your data</Badge>}
                </li>
              ))}
            </ul>
            {d.synthetic_only && <p className="mt-3 text-[13px] text-warning">This view uses only generated demo data. Paste real job descriptions to analyse your actual market.</p>}
          </Reveal>

          {d.sample_size === 0 ? <p className="text-fg-2">No job descriptions match these filters yet.</p> : (
            <>
              {d.headline && <p className="mb-8 text-[20px] font-medium tracking-tight">{d.headline}</p>}
              <div className="grid gap-12 lg:grid-cols-2">
                <FreqList title="Technical skills & technologies" rows={d.technologies} />
                <FreqList title="Other skills" rows={d.skills} />
              </div>
              <div className="mt-14 grid gap-10 md:grid-cols-3">
                <div>
                  <SectionTitle>Experience</SectionTitle>
                  <p className="text-[15px] text-fg-2">{d.experience.median_min_years != null ? <>Median minimum: <span className="font-medium text-fg">{d.experience.median_min_years} years</span></> : "Rarely specified"}</p>
                  <div className="mt-3 space-y-1 text-[13px] text-fg-2">
                    {Object.entries(d.experience.distribution ?? {}).map(([k, v]) => <p key={k}>{k} years · {v} posts</p>)}
                  </div>
                </div>
                <div>
                  <SectionTitle>Education</SectionTitle>
                  {d.education.map((e) => <p key={e.label} className="text-[14px] text-fg-2">{e.label} · {Math.round(e.share * 100)}%</p>)}
                </div>
                <div>
                  <SectionTitle>Certifications mentioned</SectionTitle>
                  {d.certifications.length ? d.certifications.map((c) => <p key={c.name} className="text-[14px] text-fg-2">{c.name} · {Math.round(c.share * 100)}%</p>) : <p className="text-[14px] text-fg-2">Rarely mentioned</p>}
                </div>
              </div>
              {d.responsibilities.length > 0 && (
                <div className="mt-14">
                  <SectionTitle>Common responsibilities</SectionTitle>
                  <ul className="space-y-2">{d.responsibilities.map((r) => <li key={r} className="text-[15px] text-fg-2">— {r}</li>)}</ul>
                </div>
              )}
            </>
          )}
          <div className="mt-14 space-y-1 border-t border-line pt-5 text-[13px] text-muted">{d.disclaimers.map((x) => <p key={x}>{x}</p>)}</div>
        </div>
      )}
      <PasteDialog open={pasteOpen} onOpenChange={setPasteOpen} careerId={f.career_id} onDone={() => analysis.refetch()} />
    </div>
  );
}

function FreqList({ title, rows }: { title: string; rows: Row[] }) {
  return (
    <div>
      <SectionTitle hint="share of postings">{title}</SectionTitle>
      <ul className="space-y-3">
        {rows.slice(0, 12).map((r, i) => (
          <Reveal key={r.skill_id} delay={i * 0.03}>
            <li className="grid grid-cols-[140px_1fr_48px_20px] items-center gap-3 text-[14px]">
              <span className="truncate">{r.name}</span>
              <div className="h-1.5 overflow-hidden rounded-full bg-[#ececec]"><div className="h-full rounded-full bg-ink" style={{ width: `${r.share * 100}%` }} /></div>
              <span className="text-right font-mono text-[12px] tabular-nums text-fg-2">{Math.round(r.share * 100)}%</span>
              <span title={r.you_have ? `You: ${r.your_level}` : "Not in your profile yet"}>{r.you_have ? <Check className="size-3.5" /> : <span className="block size-1.5 rounded-full bg-line-strong" />}</span>
            </li>
          </Reveal>
        ))}
      </ul>
      <p className="mt-3 text-[12px] text-muted">✓ = in your profile</p>
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: [string, string][] }) {
  return (
    <div>
      <Label>{label}</Label>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className={cn("focus-ring h-10 w-full rounded-lg border border-line-strong bg-surface px-3 text-[14px]")}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </div>
  );
}

function PasteDialog({ open, onOpenChange, careerId, onDone }: { open: boolean; onOpenChange: (o: boolean) => void; careerId: string; onDone: () => void }) {
  const [source, setSource] = useState("");
  const [country, setCountry] = useState("");
  const [text, setText] = useState("");
  const ingest = useMutation({
    mutationFn: () => {
      const posts = text.split(/\n-{3,}\n/).map((t) => t.trim()).filter((t) => t.length > 20).map((t) => {
        const [first, ...rest] = t.split("\n");
        return { title: first.slice(0, 200), description: rest.join("\n") || first, country: country || null, remote: /remote/i.test(t), posted_on: new Date().toISOString().slice(0, 10) };
      });
      if (!posts.length) throw new Error("Paste at least one job description (title on the first line).");
      return post("/market/ingest", { source: source || "Pasted by you", career_id: careerId || null, postings: posts });
    },
    onSuccess: () => { toast.success("Job descriptions analysed. They're private to your account."); onOpenChange(false); setText(""); onDone(); },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogTitle className="text-[20px] font-semibold tracking-tight">Analyse real job descriptions</DialogTitle>
        <DialogDescription className="mt-1 text-[14px] text-fg-2">Paste one or more postings. Put the job title on the first line and separate postings with a line of <code>---</code>. They stay private to you.</DialogDescription>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div><Label>Where are they from?</Label><Input value={source} onChange={(e) => setSource(e.target.value)} placeholder="e.g. LinkedIn search, Sep 2026" /></div>
          <div><Label>Country</Label><Input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="e.g. Germany" /></div>
        </div>
        <Textarea value={text} onChange={(e) => setText(e.target.value)} className="mt-4 min-h-[240px] font-mono text-[13px]" placeholder={"AI Engineer\nWe're looking for…\n---\nML Engineer\n…"} />
        <Button className="mt-4 w-full" onClick={() => ingest.mutate()} loading={ingest.isPending}>Extract & analyse</Button>
      </DialogContent>
    </Dialog>
  );
}
