import { Suspense } from "react";
import { CareerExplorer } from "@/components/careers/explorer";
import { PageHeader } from "@/components/ui/states";

export const metadata = { title: "Explore careers" };

export default function ExplorePage() {
  return (
    <div>
      <PageHeader eyebrow="Career universe" title="Explore careers." description="Fifty-plus careers across technology, data, business, finance, design, healthcare, research and more. Create a profile to see how each one fits you." />
      <Suspense><CareerExplorer base="/explore" /></Suspense>
    </div>
  );
}
