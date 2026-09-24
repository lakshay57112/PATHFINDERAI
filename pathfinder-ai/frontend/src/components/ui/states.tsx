"use client";

import Link from "next/link";
import { AlertCircle } from "lucide-react";
import { ApiError } from "@/lib/api";
import { Button } from "./button";
import { Skeleton } from "./primitives";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: React.ReactNode; description?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <header className="mb-10 flex flex-col gap-6 md:mb-14 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow mb-4">{eyebrow}</p>}
        <h1 className="text-title font-semibold text-fg">{title}</h1>
        {description && <p className="mt-4 text-[17px] leading-relaxed text-fg-2">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function SectionTitle({ children, hint }: { children: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <div className="mb-5 flex items-baseline justify-between gap-4">
      <h2 className="text-[20px] font-semibold tracking-tight">{children}</h2>
      {hint && <div className="text-[13px] text-muted">{hint}</div>}
    </div>
  );
}

export function LoadingBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4" aria-busy>
      <Skeleton className="h-9 w-2/5" />
      <Skeleton className="h-5 w-3/5" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-28 w-full" />
      ))}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: unknown; retry?: () => void }) {
  const msg = error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
  return (
    <div className="card flex flex-col items-start gap-4 p-6">
      <div className="flex items-center gap-2 text-fg"><AlertCircle className="size-4" /> <span className="font-medium">We hit a snag</span></div>
      <p className="text-fg-2">{msg}</p>
      {retry && <Button variant="secondary" size="sm" onClick={retry}>Try again</Button>}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: { href: string; label: string } }) {
  return (
    <div className="card flex flex-col items-start gap-3 border-dashed p-8">
      <p className="text-[17px] font-medium">{title}</p>
      {description && <p className="max-w-lg text-fg-2">{description}</p>}
      {action && (
        <Button asChild className="mt-2">
          <Link href={action.href}>{action.label}</Link>
        </Button>
      )}
    </div>
  );
}

/** Shown when a page needs a target career first. */
export function NeedsTarget() {
  return (
    <EmptyState
      title="Choose a direction first"
      description="Explore the paths that fit your profile, pick one to focus on, and we'll analyse what it takes to get there."
      action={{ href: "/app/discover", label: "Discover my paths" }}
    />
  );
}
