import { Suspense } from "react";
import { CareerExplorer } from "@/components/careers/explorer";
import { PageHeader } from "@/components/ui/states";

export default function CareersPage() {
  return (
    <div>
      <PageHeader eyebrow="Career explorer" title="Explore careers." description="Browse by field, read what each role really involves, and compare paths side by side. Nothing here is ranked as “best” — you decide what fits." />
      <Suspense><CareerExplorer base="/app/careers" /></Suspense>
    </div>
  );
}
