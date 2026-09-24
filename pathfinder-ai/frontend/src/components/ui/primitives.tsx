import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, hover, ...props }: React.HTMLAttributes<HTMLDivElement> & { hover?: boolean }) {
  return <div className={cn("card", hover && "card-hover", className)} {...props} />;
}

export function Badge({ className, tone = "default", ...props }: React.HTMLAttributes<HTMLSpanElement> & { tone?: "default" | "solid" | "success" | "warning" | "danger" | "muted" }) {
  const tones = {
    default: "border-line-strong text-fg-2 bg-surface",
    solid: "border-ink bg-ink text-white",
    success: "border-success/25 text-success bg-success/[0.06]",
    warning: "border-warning/25 text-warning bg-warning/[0.07]",
    danger: "border-danger/25 text-danger bg-danger/[0.06]",
    muted: "border-transparent bg-surface-2 text-fg-2",
  };
  return <span className={cn("inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[12px] font-medium leading-5", tones[tone], className)} {...props} />;
}

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "focus-ring h-11 w-full rounded-lg border border-line-strong bg-surface px-3.5 text-[15px] text-fg placeholder:text-muted transition-colors hover:border-[#c4c4c4] focus-visible:border-ink focus-visible:ring-0",
      className,
    )}
    {...props}
  />
));
Input.displayName = "Input";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "focus-ring min-h-[96px] w-full resize-y rounded-lg border border-line-strong bg-surface px-3.5 py-3 text-[15px] leading-relaxed text-fg placeholder:text-muted transition-colors hover:border-[#c4c4c4] focus-visible:border-ink focus-visible:ring-0",
      className,
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("mb-1.5 block text-[13px] font-medium text-fg-2", className)} {...props} />;
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-lg bg-surface-2", className)} aria-hidden>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/70 to-transparent" />
    </div>
  );
}

export function Divider({ className }: { className?: string }) {
  return <div className={cn("h-px w-full bg-line", className)} />;
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="rounded border border-line-strong bg-surface px-1.5 py-0.5 font-mono text-[11px] text-fg-2">{children}</kbd>;
}
