"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Logo } from "@/components/brand";
import { CertificateCard, CertificateForm, EvidenceList, ProjectCard, ProjectForm, useEvidenceList } from "@/components/evidence-forms";
import { ChoiceCard, Chip } from "@/components/onboarding/choice";
import { SkillsStep, type SkillLevel } from "@/components/onboarding/skills-step";
import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/primitives";
import { ApiError, post } from "@/lib/api";
import { useMe, useProfile, useVocab } from "@/lib/queries";
import type { UserCertificate, UserProject } from "@/lib/types";
import { pad2 } from "@/lib/utils";

const TOTAL = 7;
const EDU_LEVELS = ["High school", "Diploma", "Bachelor's (in progress)", "Bachelor's", "Master's (in progress)", "Master's", "PhD", "Self-taught"];
const EXP: Record<string, string> = { student: "Student", entry: "Entry level", junior: "1–2 years", mid: "3–5 years", senior: "5+ years", career_switcher: "Switching careers" };
const PREFS: Record<string, string> = { hands_on: "Hands-on practice", projects: "Building projects", video: "Video", reading: "Reading", courses: "Structured courses", mentorship: "Mentorship" };

type Draft = {
  interests: string[]; skills: Record<string, SkillLevel>; activities: string[]; work_styles: string[];
  education: { level: string; degree: string; field: string; institution: string }; experience_level: string;
  work_experience: string; internships: string; career_goals: string; hours_per_week: number; learning_preferences: string[];
};

const EMPTY: Draft = {
  interests: [], skills: {}, activities: [], work_styles: [],
  education: { level: "", degree: "", field: "", institution: "" }, experience_level: "", work_experience: "",
  internships: "", career_goals: "", hours_per_week: 8, learning_preferences: [],
};

const QUESTIONS = [
  { q: "What are you interested in?", sub: "Choose as many as you like. There are no wrong answers." },
  { q: "What technologies do you already know?", sub: "Select what you've used and tell us roughly how well. Skip anything you haven't touched." },
  { q: "What do you enjoy doing?", sub: "Think about what makes time disappear — at work, at university or in your free time." },
  { q: "What kind of work sounds interesting?", sub: "Pick the kinds of work you'd like to spend your days on." },
  { q: "Tell us about your background.", sub: "All optional. It helps us pace your roadmap and suggest realistic next steps." },
  { q: "Any certificates?", sub: "We'll look at what each one actually covers — not just count them." },
  { q: "What have you built?", sub: "Projects are the strongest evidence of your skills. Add as many as you like." },
];

const toggle = (arr: string[], v: string) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

export default function Onboarding() {
  const router = useRouter();
  const qc = useQueryClient();
  const me = useMe();
  const vocab = useVocab();
  const profile = useProfile();
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState(1);
  const [d, setD] = useState<Draft>(EMPTY);
  const [hydrated, setHydrated] = useState(false);
  const [phase, setPhase] = useState<"questions" | "analysing">("questions");
  const certs = useEvidenceList<UserCertificate>([], "/certificates");
  const projects = useEvidenceList<UserProject>([], "/projects");

  useEffect(() => {
    if (me.error instanceof ApiError && me.error.status === 401) router.replace("/login?next=/onboarding");
  }, [me.error, router]);

  // Pre-fill from an existing profile so onboarding can be revisited to update it.
  useEffect(() => {
    if (!profile.data || hydrated) return;
    const p = profile.data;
    setD({
      interests: p.interests, activities: p.activities, work_styles: p.work_styles,
      skills: Object.fromEntries(p.skills.filter((s) => s.source === "stated" || s.level > 0).map((s) => [s.skill_id, s.unsure ? "unsure" : (["", "beginner", "intermediate", "advanced"][s.level] || "beginner") as SkillLevel])),
      education: { level: p.education.level ?? "", degree: p.education.degree ?? "", field: p.education.field ?? "", institution: "" },
      experience_level: p.experience_level ?? "", work_experience: "", internships: "", career_goals: p.career_goals ?? "",
      hours_per_week: p.hours_per_week || 8, learning_preferences: p.learning_preferences,
    });
    certs.setItems(p.certificates);
    projects.setItems(p.projects.filter((x) => x.source === "user"));
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile.data]);

  const canContinue = useMemo(() => (step === 0 ? d.interests.length > 0 : true), [step, d.interests]);

  const go = (delta: number) => {
    setDir(delta);
    setStep((s) => Math.max(0, Math.min(TOTAL - 1, s + delta)));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const finish = async () => {
    setPhase("analysing");
    try {
      await post("/profile", {
        interests: d.interests, activities: d.activities, work_styles: d.work_styles,
        skills: Object.entries(d.skills).map(([skill_id, level]) => ({ skill_id, level })),
        education: { level: d.education.level || null, degree: d.education.degree || null, field: d.education.field || null, institution: d.education.institution || null },
        experience_level: d.experience_level || null, work_experience: d.work_experience || null, internships: d.internships || null,
        career_goals: d.career_goals || null, hours_per_week: d.hours_per_week, learning_preferences: d.learning_preferences,
      });
      await Promise.all([qc.invalidateQueries({ queryKey: ["me"] }), qc.invalidateQueries({ queryKey: ["profile"] }), qc.invalidateQueries({ queryKey: ["discover"] })]);
      await new Promise((r) => setTimeout(r, 2600)); // let the analysis sequence play
      router.replace("/app/profile?new=1");
    } catch (e) {
      setPhase("questions");
      toast.error(e instanceof ApiError ? e.message : "We couldn't save your profile. Please try again.");
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (e.key === "Enter" && !e.shiftKey && tag !== "TEXTAREA" && tag !== "INPUT" && phase === "questions" && canContinue) {
        step === TOTAL - 1 ? finish() : go(1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (phase === "analysing") return <Analysing name={me.data?.name} />;
  const v = vocab.data;

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 border-b border-line bg-background/80 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between">
          <Logo href="/" />
          <div className="flex items-center gap-4">
            <span className="font-mono text-[13px] tabular-nums text-fg-2">{pad2(step + 1)} / {pad2(TOTAL)}</span>
          </div>
        </div>
        <div className="h-px w-full bg-line">
          <motion.div className="h-px bg-ink" animate={{ width: `${((step + 1) / TOTAL) * 100}%` }} transition={{ duration: 0.5, ease: [0.2, 0.7, 0.2, 1] }} />
        </div>
      </header>

      <main className="container max-w-4xl pb-40 pt-14 md:pt-20">
        <AnimatePresence mode="wait" custom={dir}>
          <motion.section
            key={step}
            custom={dir}
            initial={{ opacity: 0, y: 16 * dir }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 * dir }}
            transition={{ duration: 0.4, ease: [0.2, 0.7, 0.2, 1] }}
          >
            <p className="eyebrow mb-5">Step {pad2(step + 1)}</p>
            <h1 className="text-title font-semibold">{QUESTIONS[step].q}</h1>
            <p className="mt-4 max-w-xl text-[17px] leading-relaxed text-fg-2">{QUESTIONS[step].sub}</p>

            <div className="mt-12">
              {!v ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{Array.from({ length: 9 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-xl bg-surface-2" />)}</div>
              ) : step === 0 ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {v.interests.map((o, i) => (
                    <ChoiceCard key={o.id} index={i} label={o.label} selected={d.interests.includes(o.id)} onToggle={() => setD({ ...d, interests: toggle(d.interests, o.id) })} />
                  ))}
                </div>
              ) : step === 1 ? (
                <SkillsStep vocab={v} value={d.skills} onChange={(skills) => setD({ ...d, skills })} />
              ) : step === 2 ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {v.activities.map((o, i) => (
                    <ChoiceCard key={o.id} index={i} label={o.label} selected={d.activities.includes(o.id)} onToggle={() => setD({ ...d, activities: toggle(d.activities, o.id) })} />
                  ))}
                </div>
              ) : step === 3 ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {v.work_styles.map((o, i) => (
                    <ChoiceCard key={o.id} index={i} label={o.label} selected={d.work_styles.includes(o.id)} onToggle={() => setD({ ...d, work_styles: toggle(d.work_styles, o.id) })} />
                  ))}
                </div>
              ) : step === 4 ? (
                <Background d={d} setD={setD} />
              ) : step === 5 ? (
                <div className="space-y-6">
                  <CertificateForm onAdded={certs.add} />
                  <EvidenceList>{certs.items.map((c) => <CertificateCard key={c.id} c={c} onDelete={() => certs.remove(c.id)} />)}</EvidenceList>
                </div>
              ) : (
                <div className="space-y-6">
                  <ProjectForm onAdded={projects.add} />
                  <EvidenceList>{projects.items.map((p) => <ProjectCard key={p.id} p={p} onDelete={() => projects.remove(p.id)} />)}</EvidenceList>
                </div>
              )}
            </div>
          </motion.section>
        </AnimatePresence>
      </main>

      <footer className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-background/85 pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
        <div className="container flex h-20 max-w-4xl items-center justify-between gap-3">
          <Button variant="ghost" onClick={() => go(-1)} disabled={step === 0}><ArrowLeft /> Back</Button>
          <div className="flex items-center gap-2">
            {step > 0 && step < TOTAL - 1 && <Button variant="ghost" onClick={() => go(1)}>Skip</Button>}
            {step < TOTAL - 1 ? (
              <Button size="lg" onClick={() => go(1)} disabled={!canContinue}>Continue <ArrowRight /></Button>
            ) : (
              <Button size="lg" onClick={finish}>Build my profile <Check /></Button>
            )}
          </div>
        </div>
      </footer>
    </div>
  );
}

function Background({ d, setD }: { d: Draft; setD: (d: Draft) => void }) {
  const e = d.education;
  return (
    <div className="space-y-10">
      <div>
        <p className="eyebrow mb-3">Education</p>
        <div className="flex flex-wrap gap-2">
          {EDU_LEVELS.map((l) => <Chip key={l} label={l} selected={e.level === l} onClick={() => setD({ ...d, education: { ...e, level: e.level === l ? "" : l } })} />)}
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div><Label htmlFor="deg">Degree</Label><Input id="deg" value={e.degree} onChange={(x) => setD({ ...d, education: { ...e, degree: x.target.value } })} placeholder="e.g. BCA, BSc Economics" /></div>
          <div><Label htmlFor="field">Field of study</Label><Input id="field" value={e.field} onChange={(x) => setD({ ...d, education: { ...e, field: x.target.value } })} placeholder="e.g. Computer Applications" /></div>
        </div>
      </div>
      <div>
        <p className="eyebrow mb-3">Experience</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(EXP).map(([k, l]) => <Chip key={k} label={l} selected={d.experience_level === k} onClick={() => setD({ ...d, experience_level: d.experience_level === k ? "" : k })} />)}
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div><Label htmlFor="work">Work experience</Label><Textarea id="work" value={d.work_experience} onChange={(x) => setD({ ...d, work_experience: x.target.value })} placeholder="Roles, responsibilities, anything relevant." /></div>
          <div><Label htmlFor="intern">Internships</Label><Textarea id="intern" value={d.internships} onChange={(x) => setD({ ...d, internships: x.target.value })} placeholder="Where, and what you worked on." /></div>
        </div>
      </div>
      <div>
        <Label htmlFor="goals">Career goals (optional)</Label>
        <Textarea id="goals" value={d.career_goals} onChange={(x) => setD({ ...d, career_goals: x.target.value })} placeholder="Even a rough direction helps — or leave it blank." />
      </div>
      <div className="grid gap-10 md:grid-cols-2">
        <div>
          <p className="eyebrow mb-3">Time available</p>
          <div className="flex items-baseline gap-2"><span className="text-[40px] font-semibold tabular-nums tracking-tight">{d.hours_per_week}</span><span className="text-fg-2">hours / week</span></div>
          <input type="range" min={2} max={40} step={1} value={d.hours_per_week} onChange={(x) => setD({ ...d, hours_per_week: Number(x.target.value) })}
            className="mt-3 w-full accent-black" aria-label="Hours per week" />
          <p className="mt-2 text-[13px] text-muted">Your roadmap timeline adapts to this. You can change it any time.</p>
        </div>
        <div>
          <p className="eyebrow mb-3">How you like to learn</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(PREFS).map(([k, l]) => <Chip key={k} label={l} selected={d.learning_preferences.includes(k)} onClick={() => setD({ ...d, learning_preferences: toggle(d.learning_preferences, k) })} />)}
          </div>
        </div>
      </div>
    </div>
  );
}

const AGENTS = ["Understanding your interests", "Mapping your skills and evidence", "Reading your projects and certificates", "Building your career profile", "Finding paths worth exploring"];

function Analysing({ name }: { name?: string }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(x + 1, AGENTS.length - 1)), 520);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="flex min-h-dvh items-center justify-center px-6">
      <div className="w-full max-w-md">
        <p className="eyebrow mb-6">Analysing your profile</p>
        <h1 className="text-[34px] font-semibold leading-tight tracking-[-0.03em]">
          {name ? `One moment, ${name.split(" ")[0]}.` : "One moment."}
        </h1>
        <ul className="mt-10 space-y-4">
          {AGENTS.map((a, idx) => (
            <motion.li key={a} initial={{ opacity: 0, y: 6 }} animate={{ opacity: idx <= i ? 1 : 0.25, y: 0 }} transition={{ delay: idx * 0.08 }}
              className="flex items-center gap-3 text-[15px]">
              <span className="relative flex size-4 items-center justify-center">
                {idx < i ? <Check className="size-4" /> : idx === i ? <span className="size-1.5 animate-ping rounded-full bg-ink" /> : <span className="size-1.5 rounded-full bg-line-strong" />}
              </span>
              <span className={idx <= i ? "text-fg" : "text-muted"}>{a}</span>
            </motion.li>
          ))}
        </ul>
      </div>
    </div>
  );
}
