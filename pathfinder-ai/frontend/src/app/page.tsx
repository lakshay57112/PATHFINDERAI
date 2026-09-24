"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight, BrainCircuit, Box, Briefcase, Cloud, Cog, Cpu, Database, FlaskConical, HeartPulse, Landmark, Megaphone,
  PenTool, Rocket, ShieldCheck,
} from "lucide-react";
import { Logo } from "@/components/brand";
import { CursorGlow, Magnetic, PathLines } from "@/components/landing/effects";
import { Button } from "@/components/ui/button";
import { Reveal, TextReveal } from "@/components/ui/motion";
import { useMe } from "@/lib/queries";
import { pad2 } from "@/lib/utils";

const STEPS = [
  { title: "Tell us about yourself", body: "Interests, skills, projects and certificates — skip anything you're unsure about." },
  { title: "Discover your possibilities", body: "Several paths that fit what you told us, each with the reasons it appeared." },
  { title: "Choose your direction", body: "Explore careers side by side, then pick the one you want to work toward." },
  { title: "Get your roadmap", body: "A plan built around what you already know, adapting as you make progress." },
];

const UNIVERSE = [
  { id: "technology", label: "Technology", icon: Cpu },
  { id: "data", label: "Data", icon: Database },
  { id: "ai", label: "AI", icon: BrainCircuit },
  { id: "business", label: "Business", icon: Briefcase },
  { id: "finance", label: "Finance", icon: Landmark },
  { id: "cybersecurity", label: "Cybersecurity", icon: ShieldCheck },
  { id: "design", label: "Design", icon: PenTool },
  { id: "marketing", label: "Marketing", icon: Megaphone },
  { id: "healthcare", label: "Healthcare", icon: HeartPulse },
  { id: "research", label: "Research", icon: FlaskConical },
  { id: "product", label: "Product", icon: Box },
  { id: "entrepreneurship", label: "Entrepreneurship", icon: Rocket },
  { id: "cloud", label: "Cloud", icon: Cloud },
  { id: "engineering", label: "Engineering", icon: Cog },
];

const PATHS = ["AI Engineer", "Financial Data Analyst", "FinTech AI Engineer", "Data Scientist", "Quantitative Analyst"];

export default function Landing() {
  const { data: me } = useMe();
  const startHref = me ? (me.onboarding_completed ? "/app" : "/onboarding") : "/signup";

  return (
    <div className="relative">
      {/* nav */}
      <header className="sticky top-0 z-40 border-b border-transparent bg-background/70 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <Logo />
          <nav className="flex items-center gap-1 text-sm">
            <a href="#how" className="focus-ring hidden rounded-md px-3 py-2 text-fg-2 hover:text-fg sm:block">How it works</a>
            <Link href="/explore" className="focus-ring hidden rounded-md px-3 py-2 text-fg-2 hover:text-fg sm:block">Careers</Link>
            {me ? (
              <Button asChild size="sm"><Link href="/app">Open app</Link></Button>
            ) : (
              <>
                <Link href="/login" className="focus-ring rounded-md px-3 py-2 text-fg-2 hover:text-fg">Sign in</Link>
                <Button asChild size="sm"><Link href="/signup">Get started</Link></Button>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* hero */}
      <section className="relative -mt-16 flex min-h-[100svh] items-center overflow-hidden pt-16">
        <PathLines />
        <CursorGlow />
        <div className="container relative">
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8 }} className="eyebrow mb-8">
            PathFinder AI
          </motion.p>
          <h1 className="max-w-5xl text-display font-semibold">
            <TextReveal text="Your career is not a job title." />
            <br />
            <TextReveal text="It's a path." delay={0.45} className="text-[#9a9a9a]" />
          </h1>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1, duration: 0.7 }}
            className="mt-10 max-w-xl space-y-1 text-[19px] leading-relaxed text-fg-2">
            <p>Tell us what you know.</p>
            <p>Tell us what you enjoy.</p>
            <p className="text-fg">We&apos;ll help you discover where you could go next.</p>
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.25, duration: 0.7 }}
            className="mt-12 flex flex-wrap items-center gap-3">
            <Magnetic>
              <Button asChild size="pill" className="group">
                <Link href={startHref}>
                  Discover My Path <ArrowRight className="transition-transform group-hover:translate-x-0.5" />
                </Link>
              </Button>
            </Magnetic>
            <Button asChild size="pill" variant="secondary">
              <Link href="/explore">Explore Careers</Link>
            </Button>
          </motion.div>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.8 }} className="mt-8 text-[13px] text-muted">
            No account yet? <Link href="/login?demo=1" className="underline underline-offset-4 hover:text-fg">Try the demo profile</Link>
          </motion.p>
        </div>
      </section>

      {/* how it works */}
      <section id="how" className="border-t border-line py-28 md:py-36">
        <div className="container">
          <Reveal><p className="eyebrow mb-4">How it works</p></Reveal>
          <Reveal delay={0.05}><h2 className="max-w-2xl text-title font-semibold">From &ldquo;I&apos;m not sure&rdquo; to a clear next step.</h2></Reveal>
          <div className="mt-16 grid gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <Reveal key={s.title} delay={i * 0.08} className="bg-surface p-8">
                <p className="font-mono text-[13px] text-muted">{pad2(i + 1)}</p>
                <h3 className="mt-10 text-[19px] font-semibold tracking-tight">{s.title}</h3>
                <p className="mt-3 leading-relaxed text-fg-2">{s.body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* career universe */}
      <section className="py-28 md:py-36">
        <div className="container">
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
            <div>
              <Reveal><p className="eyebrow mb-4">Career universe</p></Reveal>
              <Reveal delay={0.05}><h2 className="max-w-xl text-title font-semibold">Fifty-plus careers across fourteen fields.</h2></Reveal>
            </div>
            <Reveal delay={0.1}>
              <Link href="/explore" className="focus-ring group inline-flex items-center gap-1.5 rounded-md text-[15px] text-fg-2 hover:text-fg">
                Explore all careers <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </Reveal>
          </div>
          <div className="mt-14 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-7">
            {UNIVERSE.map((c, i) => (
              <Reveal key={c.id} delay={(i % 7) * 0.04}>
                <Link href={`/explore?category=${c.id}`} className="card card-hover focus-ring flex h-full flex-col justify-between gap-10 p-5">
                  <c.icon className="size-[18px] text-fg" strokeWidth={1.5} />
                  <span className="text-[15px] font-medium">{c.label}</span>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* transformation */}
      <section className="border-y border-line bg-surface py-28 md:py-36">
        <div className="container grid items-center gap-16 lg:grid-cols-2">
          <div>
            <Reveal><p className="eyebrow mb-4">An example</p></Reveal>
            <Reveal delay={0.05}>
              <blockquote className="text-title font-semibold">&ldquo;I like Python + finance + analytics.&rdquo;</blockquote>
            </Reveal>
            <Reveal delay={0.1}>
              <p className="mt-6 max-w-md text-[17px] leading-relaxed text-fg-2">
                You don&apos;t need a job title in mind. PathFinder connects what you enjoy with what you can already do — and shows
                <span className="text-fg"> why </span>each path appeared.
              </p>
            </Reveal>
          </div>
          <div className="relative">
            <Reveal><p className="eyebrow mb-5">Possible paths</p></Reveal>
            <ul className="space-y-2">
              {PATHS.map((p, i) => (
                <Reveal key={p} delay={0.15 + i * 0.1}>
                  <li className="card flex items-center justify-between px-5 py-4">
                    <span className="text-[17px] font-medium">{p}</span>
                    <span className="font-mono text-[12px] text-muted">{pad2(i + 1)}</span>
                  </li>
                </Reveal>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* principles */}
      <section className="py-28 md:py-32">
        <div className="container grid gap-10 md:grid-cols-3">
          {[
            ["Several paths, not one answer", "We never claim a career is objectively “best”. You explore; you decide."],
            ["Every suggestion is explained", "Each recommendation shows the evidence behind it — from your profile and our knowledge base."],
            ["Evidence over collecting badges", "Projects and real work come first. Certificates only where they fill a genuine gap."],
          ].map(([t, b], i) => (
            <Reveal key={t} delay={i * 0.08}>
              <div className="border-t border-ink pt-6">
                <h3 className="text-[17px] font-semibold tracking-tight">{t}</h3>
                <p className="mt-3 leading-relaxed text-fg-2">{b}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* final CTA */}
      <section className="relative overflow-hidden border-t border-line py-32 md:py-44">
        <CursorGlow />
        <div className="container relative text-center">
          <Reveal>
            <h2 className="mx-auto max-w-3xl text-title font-semibold">
              You don&apos;t need to know
              <br />
              where you&apos;re going yet.
            </h2>
          </Reveal>
          <Reveal delay={0.08}><p className="mt-6 text-[19px] text-fg-2">Start with what interests you.</p></Reveal>
          <Reveal delay={0.16} className="mt-12">
            <Magnetic>
              <Button asChild size="pill" className="group">
                <Link href={startHref}>Find My Path <ArrowRight className="transition-transform group-hover:translate-x-0.5" /></Link>
              </Button>
            </Magnetic>
          </Reveal>
        </div>
      </section>

      <footer className="border-t border-line py-10">
        <div className="container flex flex-col items-start justify-between gap-4 text-[13px] text-muted sm:flex-row sm:items-center">
          <Logo />
          <p>Career guidance to help you explore — not a guarantee of any outcome.</p>
        </div>
      </footer>
    </div>
  );
}
