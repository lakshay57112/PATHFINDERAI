import Link from "next/link";
import { cn } from "@/lib/utils";

/** Wordmark: a small path glyph + "PathFinder". */
export function Logo({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link href={href} className={cn("focus-ring group inline-flex items-center gap-2 rounded-md", className)} aria-label="PathFinder AI home">
      <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden>
        <rect x="0.5" y="0.5" width="21" height="21" rx="6" fill="#000" />
        <path d="M5.5 15.5 C 8 15.5, 8.5 11, 11 11 S 14 6.5, 16.5 6.5" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="5.5" cy="15.5" r="1.4" fill="#fff" />
        <circle cx="16.5" cy="6.5" r="1.4" fill="#fff" />
      </svg>
      <span className="text-[15px] font-semibold tracking-tight">PathFinder</span>
    </Link>
  );
}
