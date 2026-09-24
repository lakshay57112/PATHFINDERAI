"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function ChoiceCard({ label, selected, onToggle, hint, index = 0 }: {
  label: string; selected: boolean; onToggle: () => void; hint?: string; index?: number;
}) {
  return (
    <motion.button
      type="button"
      onClick={onToggle}
      aria-pressed={selected}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0, scale: selected ? 1.015 : 1 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.35, delay: index * 0.025, ease: [0.2, 0.7, 0.2, 1] }}
      className={cn(
        "focus-ring group relative flex min-h-[64px] items-center justify-between gap-3 rounded-xl border bg-surface px-4 py-3.5 text-left transition-[border-color,box-shadow,background-color] duration-200",
        selected ? "border-ink shadow-soft" : "border-line hover:border-line-strong",
      )}
    >
      <span>
        <span className="block text-[15px] font-medium text-fg">{label}</span>
        {hint && <span className="mt-0.5 block text-[12px] text-muted">{hint}</span>}
      </span>
      <span
        className={cn(
          "flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors",
          selected ? "border-ink bg-ink text-white" : "border-line-strong text-transparent group-hover:border-[#bbb]",
        )}
      >
        <Check className="size-3" strokeWidth={3} />
      </span>
    </motion.button>
  );
}

export function Chip({ label, selected, onClick, size = "md" }: { label: string; selected: boolean; onClick: () => void; size?: "sm" | "md" }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "focus-ring rounded-full border transition-[background-color,border-color,color,transform] duration-200 active:scale-[0.97]",
        size === "sm" ? "px-3 py-1 text-[13px]" : "px-4 py-2 text-[14px]",
        selected ? "border-ink bg-ink text-white" : "border-line-strong bg-surface text-fg-2 hover:border-[#bbb] hover:text-fg",
      )}
    >
      {label}
    </button>
  );
}
