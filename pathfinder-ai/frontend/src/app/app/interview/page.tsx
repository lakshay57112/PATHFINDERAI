"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, Check, Minus, RotateCcw } from "lucide-react";
import { Chip } from "@/components/onboarding/choice";
import { Button } from "@/components/ui/button";
import { Badge, Card, Textarea } from "@/components/ui/primitives";
import { ProgressLine } from "@/components/ui/segment-bar";
import { PageHeader } from "@/components/ui/states";
import { get, post } from "@/lib/api";
import { useProfile } from "@/lib/queries";

type Q = { id: string; prompt: string; number: number; total: number; is_follow_up: boolean };
type Eval = {
  technical_coverage: number; technical_coverage_label: string; accuracy: string; accuracy_notes: string; clarity: number; clarity_label: string;
  covered_concepts: string[]; missing_concepts: string[]; feedback: string; method: string;
};
type Turn = { q: Q; answer: string; evaluation: Eval };

const ACCURACY: Record<string, string> = { accurate: "Accurate", mostly_accurate: "Mostly accurate", contains_errors: "Contains errors", unclear: "Unclear", not_assessed: "Not assessed offline" };

export default function InterviewPage() {
  const profile = useProfile();
  const modes = useQuery({ queryKey: ["interview-modes"], queryFn: () => get<{ id: string; label: string }[]>("/interview/modes"), staleTime: Infinity });
  const [mode, setMode] = useState("technical");
  const [session, setSession] = useState<{ id: string; title: string } | null>(null);
  const [question, setQuestion] = useState<Q | null>(null);
  const [answer, setAnswer] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [summary, setSummary] = useState<{ questions_answered: number; avg_coverage: number; avg_clarity: number; note: string } | null>(null);

  const start = useMutation({
    mutationFn: () => post<{ session_id: string; title: string; question: Q }>("/interview/start", { mode }),
    onSuccess: (d) => { setSession({ id: d.session_id, title: d.title }); setQuestion(d.question); setTurns([]); setSummary(null); },
    onError: (e: Error) => toast.error(e.message),
  });
  const submit = useMutation({
    mutationFn: () => post<{ evaluation: Eval; next_question: Q | null; finished: boolean; summary: any }>("/interview/answer", { session_id: session!.id, answer }),
    onSuccess: (d) => {
      setTurns((t) => [...t, { q: question!, answer, evaluation: d.evaluation }]);
      setAnswer("");
      setQuestion(d.next_question);
      if (d.finished) setSummary(d.summary);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const last = turns[turns.length - 1];

  return (
    <div>
      <PageHeader eyebrow="Interview practice" title={session ? session.title : "Practise for the role you want."}
        description={session ? undefined : `Answer out loud or in writing. You'll get feedback on concept coverage, accuracy and clarity — then a follow-up, just like a real interview.${profile.data?.target_career_name ? ` Practising for: ${profile.data.target_career_name}.` : ""}`}
        actions={session && <Button variant="secondary" onClick={() => { setSession(null); setQuestion(null); }}><RotateCcw /> New session</Button>} />

      {!session ? (
        <Card className="p-6 md:p-8">
          <p className="eyebrow mb-4">Choose a mode</p>
          <div className="flex flex-wrap gap-2">{modes.data?.map((m) => <Chip key={m.id} label={m.label} selected={mode === m.id} onClick={() => setMode(m.id)} />)}</div>
          <Button size="lg" className="mt-8" onClick={() => start.mutate()} loading={start.isPending}>Start interview <ArrowRight /></Button>
          {!profile.data?.target_career_id && <p className="mt-4 text-[13px] text-muted">Choose a target career first so questions match the role.</p>}
        </Card>
      ) : (
        <div className="grid gap-10 lg:grid-cols-[1.3fr_1fr]">
          <div>
            <AnimatePresence mode="wait">
              {question ? (
                <motion.div key={question.prompt} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
                  <div className="mb-4 flex items-center gap-3">
                    <span className="font-mono text-[12px] text-muted">Q{question.number} / {question.total}</span>
                    {question.is_follow_up && <Badge tone="muted">Follow-up</Badge>}
                  </div>
                  <ProgressLine value={(question.number - 1) / question.total} className="mb-8 max-w-xs" />
                  <h2 className="text-[26px] font-semibold leading-snug tracking-[-0.02em]">{question.prompt}</h2>
                  <Textarea value={answer} onChange={(e) => setAnswer(e.target.value)} placeholder="Structure your answer: the idea, how it works, trade-offs, an example…" className="mt-8 min-h-[220px]" />
                  <div className="mt-3 flex items-center justify-between">
                    <span className="text-[12px] text-muted">{answer.trim().split(/\s+/).filter(Boolean).length} words</span>
                    <Button onClick={() => submit.mutate()} loading={submit.isPending} disabled={answer.trim().length < 3}>Submit answer</Button>
                  </div>
                </motion.div>
              ) : summary && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <p className="eyebrow mb-4">Session complete</p>
                  <h2 className="text-[30px] font-semibold tracking-tight">Nice work — {summary.questions_answered} answers.</h2>
                  <div className="mt-8 grid max-w-md grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line">
                    <div className="bg-surface p-5"><p className="text-[30px] font-semibold tabular-nums">{summary.avg_coverage}%</p><p className="text-[13px] text-fg-2">Avg. concept coverage</p></div>
                    <div className="bg-surface p-5"><p className="text-[30px] font-semibold tabular-nums">{summary.avg_clarity}%</p><p className="text-[13px] text-fg-2">Avg. clarity</p></div>
                  </div>
                  <p className="mt-4 text-[13px] text-muted">{summary.note}</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <aside className="lg:sticky lg:top-10 lg:h-fit">
            {last ? <Feedback e={last.evaluation} /> : <p className="text-[14px] text-fg-2">Feedback appears here after each answer. Strong answers are saved as assessment evidence on your Progress page.</p>}
          </aside>
        </div>
      )}
    </div>
  );
}

function Feedback({ e }: { e: Eval }) {
  return (
    <motion.div key={e.feedback} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card p-6">
      <p className="eyebrow mb-5">Feedback</p>
      <div className="grid grid-cols-3 gap-4">
        <Metric label="Technical coverage" value={`${e.technical_coverage}%`} sub={e.technical_coverage_label} />
        <Metric label="Accuracy" value={ACCURACY[e.accuracy] ?? e.accuracy} small />
        <Metric label="Clarity" value={`${e.clarity}%`} sub={e.clarity_label} />
      </div>
      <p className="mt-6 text-[14.5px] leading-relaxed">{e.feedback}</p>
      {e.covered_concepts.length > 0 && (
        <ul className="mt-5 space-y-1.5">{e.covered_concepts.map((c) => <li key={c} className="flex gap-2 text-[13.5px]"><Check className="mt-0.5 size-3.5 shrink-0 text-success" />{c}</li>)}</ul>
      )}
      {e.missing_concepts.length > 0 && (
        <>
          <p className="eyebrow mb-2 mt-5">Missing concepts</p>
          <ul className="space-y-1.5">{e.missing_concepts.map((c) => <li key={c} className="flex gap-2 text-[13.5px] text-fg-2"><Minus className="mt-0.5 size-3.5 shrink-0" />{c}</li>)}</ul>
        </>
      )}
      <p className="mt-6 border-t border-line pt-4 text-[12px] text-muted">{e.method === "llm_rubric" ? "Evaluated by AI against a concept rubric." : e.accuracy_notes}</p>
    </motion.div>
  );
}

function Metric({ label, value, sub, small }: { label: string; value: string; sub?: string; small?: boolean }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wider text-muted">{label}</p>
      <p className={small ? "mt-1 text-[14px] font-medium leading-tight" : "mt-1 text-[24px] font-semibold tabular-nums tracking-tight"}>{value}</p>
      {sub && <p className="text-[12px] text-fg-2">{sub}</p>}
    </div>
  );
}
