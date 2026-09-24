"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  Award, BarChart3, BookOpen, Compass, FolderGit2, Home, LogOut, Map, MessageCircle, Mic, Radar, Settings, Target, TrendingUp, User,
} from "lucide-react";
import { Logo } from "@/components/brand";
import { post } from "@/lib/api";
import { useMe } from "@/lib/queries";
import { cn } from "@/lib/utils";

export const NAV = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/app/discover", label: "Discover", icon: Compass },
  { href: "/app/careers", label: "Careers", icon: Radar },
  { href: "/app/roadmap", label: "My Roadmap", icon: Map },
  { href: "/app/projects", label: "Projects", icon: FolderGit2 },
  { href: "/app/learning", label: "Learning", icon: BookOpen },
  { href: "/app/certificates", label: "Certificates", icon: Award },
  { href: "/app/mentor", label: "AI Mentor", icon: MessageCircle },
  { href: "/app/progress", label: "Progress", icon: TrendingUp },
  { href: "/app/profile", label: "Profile", icon: User },
  { href: "/app/settings", label: "Settings", icon: Settings },
];

const MORE = [
  { href: "/app/gap", label: "Skill gaps", icon: Target },
  { href: "/app/interview", label: "Interview practice", icon: Mic },
  { href: "/app/market", label: "Job market", icon: BarChart3 },
];

const MOBILE = [
  { href: "/app", label: "Home", icon: Home },
  { href: "/app/discover", label: "Discover", icon: Compass },
  { href: "/app/roadmap", label: "Roadmap", icon: Map },
  { href: "/app/mentor", label: "Mentor", icon: MessageCircle },
  { href: "/app/profile", label: "Profile", icon: User },
];

function isActive(path: string, href: string) {
  return href === "/app" ? path === "/app" : path === href || path.startsWith(href + "/");
}

function Item({ href, label, icon: Icon, active }: { href: string; label: string; icon: any; active: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "focus-ring group relative flex items-center gap-3 rounded-lg px-3 py-[7px] text-[14px] transition-colors",
        active ? "bg-surface text-fg shadow-soft ring-1 ring-line" : "text-fg-2 hover:bg-surface-2 hover:text-fg",
      )}
    >
      <Icon className={cn("size-[16px]", active ? "text-fg" : "text-muted group-hover:text-fg-2")} strokeWidth={1.6} />
      {label}
    </Link>
  );
}

export function Sidebar() {
  const path = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const logout = async () => {
    await post("/auth/logout").catch(() => {});
    qc.clear();
    router.replace("/");
  };
  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-line bg-background/60 px-3 py-5 backdrop-blur lg:flex">
      <div className="px-3 pb-7"><Logo href="/app" /></div>
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto" aria-label="Main">
        {NAV.map((n) => <Item key={n.href} {...n} active={isActive(path, n.href)} />)}
        <p className="eyebrow mb-2 mt-7 px-3">Practice & insight</p>
        {MORE.map((n) => <Item key={n.href} {...n} active={isActive(path, n.href)} />)}
      </nav>
      <div className="mt-4 flex items-center justify-between gap-2 border-t border-line px-3 pt-4">
        <div className="min-w-0">
          <p className="truncate text-[13px] font-medium">{me?.name || "You"}</p>
          <p className="truncate text-[12px] text-muted">{me?.is_demo ? "Demo profile" : me?.email}</p>
        </div>
        <button onClick={logout} className="focus-ring rounded-md p-1.5 text-muted hover:bg-surface-2 hover:text-fg" aria-label="Sign out" title="Sign out">
          <LogOut className="size-4" />
        </button>
      </div>
    </aside>
  );
}

export function MobileNav() {
  const path = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-background/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-md lg:hidden" aria-label="Main">
      <div className="grid grid-cols-5">
        {MOBILE.map(({ href, label, icon: Icon }) => {
          const active = isActive(path, href);
          return (
            <Link key={href} href={href} className={cn("focus-ring flex flex-col items-center gap-1 py-2.5 text-[11px]", active ? "text-fg" : "text-muted")}>
              <Icon className="size-5" strokeWidth={active ? 2 : 1.6} />
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

export function MobileTopBar() {
  return (
    <div className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-background/85 px-5 backdrop-blur-md lg:hidden">
      <Logo href="/app" />
      <div className="flex gap-1">
        <Link href="/app/progress" className="focus-ring rounded-md p-2 text-fg-2" aria-label="Progress"><TrendingUp className="size-5" strokeWidth={1.6} /></Link>
        <Link href="/app/settings" className="focus-ring rounded-md p-2 text-fg-2" aria-label="Settings"><Settings className="size-5" strokeWidth={1.6} /></Link>
      </div>
    </div>
  );
}
