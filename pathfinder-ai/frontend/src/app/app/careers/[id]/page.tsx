"use client";

import { use } from "react";
import { CareerDetailView } from "@/components/careers/career-detail";

export default function CareerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <CareerDetailView id={id} />;
}
