"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

/** Grayscale glow that softly follows the cursor inside its parent. */
export function CursorGlow() {
  const x = useMotionValue(-400);
  const y = useMotionValue(-400);
  const sx = useSpring(x, { stiffness: 60, damping: 20, mass: 0.6 });
  const sy = useSpring(y, { stiffness: 60, damping: 20, mass: 0.6 });
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el) return;
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      x.set(e.clientX - r.left);
      y.set(e.clientY - r.top);
    };
    el.addEventListener("pointermove", move);
    return () => el.removeEventListener("pointermove", move);
  }, [x, y]);
  const bg = useTransform([sx, sy], ([a, b]) => `radial-gradient(520px circle at ${a}px ${b}px, rgba(0,0,0,0.055), transparent 60%)`);
  return <motion.div ref={ref} aria-hidden className="pointer-events-none absolute inset-0" style={{ background: bg }} />;
}

/** Button wrapper that is gently attracted to the cursor. */
export function Magnetic({ children, strength = 0.28, className }: { children: React.ReactNode; strength?: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const x = useSpring(0, { stiffness: 220, damping: 16 });
  const y = useSpring(0, { stiffness: 220, damping: 16 });
  return (
    <motion.div
      ref={ref}
      className={cn("inline-block", className)}
      style={{ x, y }}
      onPointerMove={(e) => {
        const r = ref.current!.getBoundingClientRect();
        x.set((e.clientX - (r.left + r.width / 2)) * strength);
        y.set((e.clientY - (r.top + r.height / 2)) * strength);
      }}
      onPointerLeave={() => {
        x.set(0);
        y.set(0);
      }}
    >
      {children}
    </motion.div>
  );
}

// Laid out to rise through the empty lower-right of the hero (never behind the headline).
const NODES = [
  { id: "interests", label: "Interests", x: 560, y: 570 },
  { id: "skills", label: "Skills", x: 720, y: 440 },
  { id: "career", label: "Career", x: 900, y: 440 },
  { id: "projects", label: "Projects", x: 1060, y: 310 },
  { id: "future", label: "Future", x: 1150, y: 170 },
];
const PATHS = [
  "M560 570 C 610 520, 650 440, 720 440",
  "M720 440 L 900 440",
  "M900 440 C 980 440, 1000 310, 1060 310",
  "M1060 310 C 1110 310, 1120 170, 1150 170",
];

/** A thin, slowly drawn career-path line behind the hero. Deliberately faint. */
export function PathLines() {
  return (
    <svg aria-hidden className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 1300 700" preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern id="dots" width="28" height="28" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.9" fill="#000" opacity="0.06" />
        </pattern>
        <linearGradient id="fade" x1="0" x2="1">
          <stop offset="0" stopColor="#000" stopOpacity="0" />
          <stop offset="0.25" stopColor="#000" stopOpacity="0.28" />
          <stop offset="1" stopColor="#000" stopOpacity="0.12" />
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#dots)" />
      {PATHS.map((d, i) => (
        <g key={i}>
          <motion.path d={d} fill="none" stroke="url(#fade)" strokeWidth={1}
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.4, delay: 0.5 + i * 0.55, ease: [0.4, 0, 0.2, 1] }} />
          <motion.path d={d} fill="none" stroke="#000" strokeWidth={1.25} strokeLinecap="round" strokeOpacity={0.35}
            strokeDasharray="0.06 1" pathLength={1}
            initial={{ strokeDashoffset: 1 }} animate={{ strokeDashoffset: [1, -0.06] }}
            transition={{ duration: 5.5, delay: 3 + i * 1.3, repeat: Infinity, repeatDelay: 4, ease: "linear" }} />
        </g>
      ))}
      {NODES.map((n, i) => (
        <motion.g key={n.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 + i * 0.55, duration: 0.8 }}>
          <circle cx={n.x} cy={n.y} r={4} fill="#fafafa" stroke="#000" strokeOpacity={0.35} />
          <text x={n.x + 12} y={n.y - 10} fontSize={11} fontFamily="var(--font-geist-mono)" letterSpacing="0.14em" fill="#000" fillOpacity={0.32}>
            {n.label.toUpperCase()}
          </text>
        </motion.g>
      ))}
    </svg>
  );
}
