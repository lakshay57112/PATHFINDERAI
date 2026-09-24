import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const pad2 = (n: number) => String(n).padStart(2, "0");

export const LEVEL_LABEL: Record<number, string> = { 0: "Not yet", 1: "Beginner", 2: "Intermediate", 3: "Advanced" };

export function greeting(date = new Date()) {
  const h = date.getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export function pct(v: number | null | undefined) {
  return `${Math.round((v ?? 0) * 100)}%`;
}

export function joinNatural(items: string[]) {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
