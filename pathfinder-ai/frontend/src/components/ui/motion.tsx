"use client";

import { motion, type HTMLMotionProps } from "framer-motion";
import * as React from "react";

const ease = [0.2, 0.7, 0.2, 1] as const;

export function Reveal({ children, delay = 0, y = 12, className, once = true, ...rest }: HTMLMotionProps<"div"> & { delay?: number; y?: number; once?: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once, margin: "-60px" }}
      transition={{ duration: 0.6, delay, ease }}
      className={className}
      {...rest}
    >
      {children}
    </motion.div>
  );
}

export function Stagger({ children, className, gap = 0.06 }: { children: React.ReactNode; className?: string; gap?: number }) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="show"
      variants={{ hidden: {}, show: { transition: { staggerChildren: gap } } }}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.5, ease } } }}
    >
      {children}
    </motion.div>
  );
}

/** Word-by-word text reveal for headlines. */
export function TextReveal({ text, className, delay = 0 }: { text: string; className?: string; delay?: number }) {
  const words = text.split(" ");
  return (
    <span className={className} aria-label={text}>
      {words.map((w, i) => (
        <span key={i} className="inline-block overflow-hidden pb-[0.08em] align-bottom" aria-hidden>
          <motion.span
            className="inline-block"
            initial={{ y: "105%" }}
            animate={{ y: 0 }}
            transition={{ duration: 0.75, delay: delay + i * 0.06, ease }}
          >
            {w}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        </span>
      ))}
    </span>
  );
}
