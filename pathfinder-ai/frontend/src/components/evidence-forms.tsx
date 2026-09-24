"use client";

import { AnimatePresence, motion } from "framer-motion";
import { FileUp, FolderGit2 as Github, Link2, Trash2 } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge, Input, Label, Textarea } from "@/components/ui/primitives";
import { ApiError, del, post, upload } from "@/lib/api";
import type { UserCertificate, UserProject } from "@/lib/types";

/* ------------------------------------------------------------------ certificates */
export function CertificateCard({ c, onDelete }: { c: UserCertificate; onDelete?: () => void }) {
  const a = c.analysis;
  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[16px] font-medium">{c.name}</p>
          <p className="mt-0.5 text-[13px] text-fg-2">
            {[a.provider ?? c.issuer, c.completed_on && new Date(c.completed_on).toLocaleDateString(undefined, { month: "short", year: "numeric" })].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {a.level && <Badge>{a.level}</Badge>}
          {onDelete && (
            <button onClick={onDelete} className="focus-ring rounded p-1 text-muted hover:text-fg" aria-label="Remove certificate"><Trash2 className="size-4" /></button>
          )}
        </div>
      </div>
      {a.demonstrates && <p className="mt-3 text-[14px] leading-relaxed text-fg-2">{a.demonstrates}</p>}
      {!!a.skills_covered?.length && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {a.skills_covered.map((s) => <Badge key={s.skill_id} tone="muted">{s.name}</Badge>)}
        </div>
      )}
      <p className="mt-3 text-[12px] text-muted">
        {a.matched_catalog ? `Matched to “${a.certificate}” in our certificate catalog.` : "Not in our catalog — skills inferred from its name and contents."}
        {c.has_file && " · File stored encrypted."}
      </p>
    </motion.div>
  );
}

export function CertificateForm({ onAdded }: { onAdded: (c: UserCertificate) => void }) {
  const [name, setName] = useState("");
  const [issuer, setIssuer] = useState("");
  const [date, setDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = async () => {
    if (name.trim().length < 2) return toast.error("Add the certificate name.");
    setBusy(true);
    try {
      let c: UserCertificate;
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("name", name);
        if (issuer) fd.append("issuer", issuer);
        if (date) fd.append("completed_on", date);
        c = await upload<UserCertificate>("/certificates/upload", fd);
      } else {
        c = await post<UserCertificate>("/certificates", { name, issuer: issuer || null, completed_on: date || null });
      }
      onAdded(c);
      setName(""); setIssuer(""); setDate(""); setFile(null);
      if (fileRef.current) fileRef.current.value = "";
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Couldn't add that certificate.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card space-y-4 p-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Label htmlFor="cert-name">Certificate name</Label>
          <Input id="cert-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Machine Learning Specialization" />
        </div>
        <div>
          <Label htmlFor="cert-issuer">Issuing organisation</Label>
          <Input id="cert-issuer" value={issuer} onChange={(e) => setIssuer(e.target.value)} placeholder="e.g. Coursera" />
        </div>
        <div>
          <Label htmlFor="cert-date">Completion date</Label>
          <Input id="cert-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="focus-ring inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-line-strong px-3 py-2 text-[13px] text-fg-2 hover:border-ink hover:text-fg">
          <FileUp className="size-4" />
          {file ? file.name : "Upload PDF or image (optional)"}
          <input ref={fileRef} type="file" accept=".pdf,image/png,image/jpeg,image/webp" className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        <Button onClick={submit} loading={busy} size="sm">Analyse & add</Button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ projects */
export function ProjectCard({ p, onDelete }: { p: UserProject; onDelete?: () => void }) {
  const a = p.analysis;
  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="card p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-[16px] font-medium">{p.name}</p>
          <p className="mt-0.5 line-clamp-2 text-[14px] text-fg-2">{p.description}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {a.difficulty && <Badge>{a.difficulty}</Badge>}
          {p.source === "recommended" && <Badge tone="solid">Roadmap</Badge>}
          {onDelete && <button onClick={onDelete} className="focus-ring rounded p-1 text-muted hover:text-fg" aria-label="Remove project"><Trash2 className="size-4" /></button>}
        </div>
      </div>
      {!!a.skills_demonstrated?.length && (
        <div className="mt-4">
          <p className="eyebrow mb-2">Skills demonstrated</p>
          <div className="flex flex-wrap gap-1.5">{a.skills_demonstrated.map((s) => <Badge key={s.skill_id} tone="muted">{s.name}</Badge>)}</div>
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[13px] text-fg-2">
        {!!a.domain_labels?.length && <span>Domain: {a.domain_labels.join(", ")}</span>}
        {!!a.career_relevance?.length && <span>Relevant to: {a.career_relevance.map((r) => r.name).join(", ")}</span>}
        {p.github_url && <a href={p.github_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-fg"><Github className="size-3.5" />Repo</a>}
        {p.demo_url && <a href={p.demo_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-fg"><Link2 className="size-3.5" />Demo</a>}
      </div>
    </motion.div>
  );
}

export function ProjectForm({ onAdded, compact }: { onAdded: (p: UserProject) => void; compact?: boolean }) {
  const [f, setF] = useState({ name: "", description: "", technologies: "", role: "", github_url: "", demo_url: "" });
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [k]: e.target.value });

  const submit = async () => {
    if (f.name.trim().length < 2) return toast.error("Give your project a name.");
    setBusy(true);
    try {
      const p = await post<UserProject>("/projects", {
        name: f.name, description: f.description, role: f.role || null,
        technologies: f.technologies.split(",").map((t) => t.trim()).filter(Boolean),
        github_url: f.github_url || null, demo_url: f.demo_url || null,
      });
      onAdded(p);
      setF({ name: "", description: "", technologies: "", role: "", github_url: "", demo_url: "" });
    } catch (e) {
      const msg = e instanceof ApiError && e.code === "validation_error" ? "Check the links — they should start with https://" : e instanceof Error ? e.message : "Couldn't add project.";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card space-y-4 p-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <div><Label htmlFor="p-name">Project name</Label><Input id="p-name" value={f.name} onChange={set("name")} placeholder="e.g. Fraud Detection" /></div>
        <div><Label htmlFor="p-role">Your role</Label><Input id="p-role" value={f.role} onChange={set("role")} placeholder="e.g. Solo developer" /></div>
        <div className="sm:col-span-2">
          <Label htmlFor="p-desc">What did you build?</Label>
          <Textarea id="p-desc" value={f.description} onChange={set("description")} placeholder="The problem, your approach and the result. The more specific, the better the analysis." className={compact ? "min-h-[80px]" : ""} />
        </div>
        <div className="sm:col-span-2"><Label htmlFor="p-tech">Technologies</Label><Input id="p-tech" value={f.technologies} onChange={set("technologies")} placeholder="Python, scikit-learn, FastAPI" /></div>
        <div><Label htmlFor="p-gh">GitHub URL</Label><Input id="p-gh" value={f.github_url} onChange={set("github_url")} placeholder="https://github.com/…" /></div>
        <div><Label htmlFor="p-demo">Demo URL</Label><Input id="p-demo" value={f.demo_url} onChange={set("demo_url")} placeholder="https://…" /></div>
      </div>
      <div className="flex justify-end"><Button onClick={submit} loading={busy} size="sm">Analyse & add</Button></div>
    </div>
  );
}

export function useEvidenceList<T extends { id: string }>(initial: T[], path: "/certificates" | "/projects") {
  const [items, setItems] = useState<T[]>(initial);
  const add = (x: T) => setItems((xs) => [...xs, x]);
  const remove = async (id: string) => {
    try {
      await del(`${path}/${id}`);
      setItems((xs) => xs.filter((x) => x.id !== id));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Couldn't remove it.");
    }
  };
  return { items, setItems, add, remove };
}

export function EvidenceList({ children }: { children: React.ReactNode }) {
  return <div className="space-y-3"><AnimatePresence initial={false}>{children}</AnimatePresence></div>;
}
