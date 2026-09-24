"use client";

import { motion, useInView } from "framer-motion";
import { useRef } from "react";
import { cn } from "@/lib/utils";

/**
 * The PathFinder signature bar: ten discrete segments (█████████░) that fill in
 * sequence when scrolled into view. `value` is 0–10.
 */
export function SegmentBar({ value, segments = 10, className, size = "md", tone = "ink", delay = 0 }: {
  value: number;
  segments?: number;
  className?: string;
  size?: "sm" | "md";
  tone?: "ink" | "muted";
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const filled = Math.round(Math.max(0, Math.min(segments, value)));
  return (
    <div ref={ref} className={cn("flex gap-[3px]", className)} role="meter" aria-valuemin={0} aria-valuemax={segments} aria-valuenow={filled}>
      {Array.from({ length: segments }).map((_, i) => (
        <div key={i} className={cn("relative flex-1 overflow-hidden rounded-[2px] bg-[#ececec]", size === "sm" ? "h-1.5" : "h-2.5")}>
          <motion.div
            className={cn("absolute inset-0", tone === "ink" ? "bg-ink" : "bg-[#a9a9a9]")}
            initial={{ scaleX: 0 }}
            animate={{ scaleX: inView && i < filled ? 1 : 0 }}
            style={{ originX: 0 }}
            transition={{ duration: 0.28, delay: delay + i * 0.045, ease: [0.2, 0.7, 0.2, 1] }}
          />
        </div>
      ))}
    </div>
  );
}

/** Thin continuous progress line that animates on view. */
export function ProgressLine({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  return (
    <div ref={ref} className={cn("h-1 w-full overflow-hidden rounded-full bg-[#ececec]", className)}>
      <motion.div
        className="h-full rounded-full bg-ink"
        initial={{ width: 0 }}
        animate={{ width: inView ? `${Math.max(0, Math.min(1, value)) * 100}%` : 0 }}
        transition={{ duration: 1.1, ease: [0.2, 0.7, 0.2, 1] }}
      />
    </div>
  );
}
