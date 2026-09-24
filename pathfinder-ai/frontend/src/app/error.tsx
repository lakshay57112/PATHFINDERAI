"use client";

import { Button } from "@/components/ui/button";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex min-h-dvh flex-col items-start justify-center gap-6 px-8 md:px-24">
      <p className="eyebrow">Something went wrong</p>
      <h1 className="text-title font-semibold">We hit an unexpected snag.</h1>
      <p className="text-fg-2">It&apos;s not you. Please try again — your data is safe.</p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
