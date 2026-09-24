"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Plus, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/primitives";
import type { Vocab } from "@/lib/types";
import { cn } from "@/lib/utils";

export type SkillLevel = "beginner" | "intermediate" | "advanced" | "unsure";
const LEVELS: { id: SkillLevel; label: string }[] = [
  { id: "beginner", label: "Beginner" },
  { id: "intermediate", label: "Intermediate" },
  { id: "advanced", label: "Advanced" },
  { id: "unsure", label: "I'm not sure" },
];

function SkillRow({ name, level, onLevel, onRemove }: { name: string; level: SkillLevel; onLevel: (l: SkillLevel) => void; onRemove: () => void }) {
  return (
    <motion.div layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }}
      className="flex flex-col gap-3 border-b border-line py-3 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-2">
        <button type="button" onClick={onRemove} className="focus-ring rounded p-0.5 text-muted hover:text-fg" aria-label={`Remove ${name}`}>
          <X className="size-3.5" />
        </button>
        <span className="text-[15px] font-medium">{name}</span>
      </div>
      <div className="flex rounded-lg border border-line bg-surface-2 p-0.5" role="radiogroup" aria-label={`${name} level`}>
        {LEVELS.map((l) => (
          <button key={l.id} type="button" role="radio" aria-checked={level === l.id} onClick={() => onLevel(l.id)}
            className={cn("focus-ring rounded-md px-2.5 py-1 text-[12.5px] transition-colors",
              level === l.id ? "bg-surface text-fg shadow-soft" : "text-fg-2 hover:text-fg")}>
            {l.label}
          </button>
        ))}
      </div>
    </motion.div>
  );
}

export function SkillsStep({ vocab, value, onChange }: { vocab: Vocab; value: Record<string, SkillLevel>; onChange: (v: Record<string, SkillLevel>) => void }) {
  const [q, setQ] = useState("");
  const names = useMemo(() => Object.fromEntries(vocab.all_skills.map((s) => [s.id, s.name])), [vocab]);
  const toggle = (id: string) => {
    const next = { ...value };
    if (next[id]) delete next[id];
    else next[id] = "beginner";
    onChange(next);
  };
  const groups: [string, { id: string; name: string }[]][] = [
    ["Languages", vocab.skill_groups.languages],
    ["AI & data", vocab.skill_groups.ai_data],
    ["Tools & platforms", vocab.skill_groups.tools],
  ];
  const results = q.trim().length > 1
    ? vocab.all_skills.filter((s) => s.name.toLowerCase().includes(q.toLowerCase()) && !value[s.id]).slice(0, 6)
    : [];
  const selected = Object.keys(value);

  return (
    <div className="grid gap-10 lg:grid-cols-[1.1fr_1fr]">
      <div className="space-y-7">
        {groups.map(([title, items]) => (
          <div key={title}>
            <p className="eyebrow mb-3">{title}</p>
            <div className="flex flex-wrap gap-2">
              {items.map((s) => (
                <button key={s.id} type="button" onClick={() => toggle(s.id)} aria-pressed={!!value[s.id]}
                  className={cn("focus-ring rounded-full border px-3.5 py-1.5 text-[14px] transition-[background-color,border-color,color,transform] duration-200 active:scale-[0.97]",
                    value[s.id] ? "border-ink bg-ink text-white" : "border-line-strong bg-surface text-fg-2 hover:border-[#bbb] hover:text-fg")}>
                  {s.name}
                </button>
              ))}
            </div>
          </div>
        ))}
        <div>
          <p className="eyebrow mb-3">Something else?</p>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search 100 skills — e.g. Figma, Excel, Spark" className="pl-10" />
          </div>
          {results.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {results.map((s) => (
                <button key={s.id} type="button" onClick={() => { toggle(s.id); setQ(""); }}
                  className="focus-ring inline-flex items-center gap-1 rounded-full border border-dashed border-line-strong px-3 py-1.5 text-[13px] text-fg-2 hover:border-ink hover:text-fg">
                  <Plus className="size-3" /> {s.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="card h-fit p-5 lg:sticky lg:top-28">
        <div className="mb-2 flex items-baseline justify-between">
          <p className="text-[15px] font-medium">Your level</p>
          <p className="font-mono text-[12px] text-muted">{selected.length} selected</p>
        </div>
        {selected.length === 0 ? (
          <p className="py-6 text-[14px] leading-relaxed text-fg-2">
            Pick anything you&apos;ve used — even a little. You don&apos;t need to know everything, and &ldquo;I&apos;m not sure&rdquo; is a perfectly good answer.
          </p>
        ) : (
          <AnimatePresence initial={false}>
            {selected.map((id) => (
              <SkillRow key={id} name={names[id] ?? id} level={value[id]} onLevel={(l) => onChange({ ...value, [id]: l })} onRemove={() => toggle(id)} />
            ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
