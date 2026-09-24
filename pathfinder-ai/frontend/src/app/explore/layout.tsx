import Link from "next/link";
import { Logo } from "@/components/brand";
import { Button } from "@/components/ui/button";

export default function ExploreLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <header className="sticky top-0 z-40 border-b border-line bg-background/80 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between">
          <Logo />
          <Button asChild size="sm"><Link href="/signup">Discover my path</Link></Button>
        </div>
      </header>
      <main className="container max-w-[1120px] pb-24 pt-14">{children}</main>
    </div>
  );
}
