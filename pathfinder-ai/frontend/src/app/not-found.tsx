import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-start justify-center gap-6 px-8 md:px-24">
      <p className="eyebrow">404</p>
      <h1 className="text-title font-semibold">This path doesn&apos;t lead anywhere.</h1>
      <p className="text-fg-2">The page you&apos;re looking for doesn&apos;t exist or has moved.</p>
      <Button asChild><Link href="/">Back to PathFinder</Link></Button>
    </div>
  );
}
