"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Magnetic } from "@/components/landing/effects";
import { Button } from "@/components/ui/button";
import { TextReveal } from "@/components/ui/motion";
import { Input } from "@/components/ui/primitives";
import { ErrorState, LoadingBlock } from "@/components/ui/states";
import { useCareer, useGenerateRoadmap, useProfile, useSelectCareer } from "@/lib/queries";

export default function SelectCareer({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const career = useCareer(id);
  const profile = useProfile();
  const select = useSelectCareer();
  const generate = useGenerateRoadmap();
  const router = useRouter();
  const [hours, setHours] = useState<number | null>(null);
  const h = hours ?? profile.data?.hours_per_week ?? 8;
  const switching = profile.data?.target_career_id && profile.data.target_career_id !== id ? profile.data.target_career_name : null;

  if (career.isLoading) return <LoadingBlock rows={1} />;
  if (career.error || !career.data) return <ErrorState error={career.error} retry={career.refetch} />;

  const build = async () => {
    await select.mutateAsync(id);
    await generate.mutateAsync({ career_id: id, hours_per_week: h });
    router.push("/app/gap?fresh=1");
  };

  return (
    <div className="flex min-h-[70vh] flex-col justify-center">
      <Link href={`/app/careers/${id}`} className="focus-ring mb-16 inline-flex w-fit items-center gap-1.5 rounded text-[13px] text-fg-2 hover:text-fg"><ArrowLeft className="size-3.5" /> Back to career</Link>
      <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="eyebrow mb-6">Your selected direction</motion.p>
      <h1 className="text-display font-semibold"><TextReveal text={career.data.name} /></h1>
      <motion.p initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="mt-8 max-w-xl text-[22px] leading-snug text-fg-2">
        Now let&apos;s understand <span className="text-fg">what it takes to get there.</span>
      </motion.p>
      {switching && (
        <p className="mt-6 max-w-xl text-[14px] text-fg-2">
          You&apos;re switching from <span className="font-medium text-fg">{switching}</span>. We&apos;ll recalculate your roadmap and carry over everything you&apos;ve already completed.
        </p>
      )}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="mt-14 flex flex-wrap items-end gap-6">
        <div>
          <label htmlFor="h" className="eyebrow mb-2 block">Hours per week</label>
          <Input id="h" type="number" min={1} max={80} value={h} onChange={(e) => setHours(Math.max(1, Math.min(80, Number(e.target.value) || 1)))} className="w-28" />
        </div>
        <Magnetic>
          <Button size="pill" onClick={build} loading={select.isPending || generate.isPending}>Build My Roadmap <ArrowRight /></Button>
        </Magnetic>
      </motion.div>
    </div>
  );
}
