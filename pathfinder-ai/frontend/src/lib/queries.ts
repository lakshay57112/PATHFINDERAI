"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, get, patch, post } from "./api";
import type {
  CareerCard, CareerDetail, CareerMatch, Dashboard, GapReport, Me, Profile, ProfileAnalysis, ProgressData, Readiness,
  Recommendations, Roadmap, Vocab,
} from "./types";

export const qk = {
  me: ["me"] as const,
  vocab: ["vocab"] as const,
  profile: ["profile"] as const,
  analysis: ["analysis"] as const,
  dashboard: ["dashboard"] as const,
  roadmap: ["roadmap"] as const,
  gap: (id?: string) => ["gap", id ?? "target"] as const,
  readiness: ["readiness"] as const,
  progress: ["progress"] as const,
  recs: ["recommendations"] as const,
  learning: ["learning"] as const,
  careers: (cat?: string, q?: string) => ["careers", cat ?? "all", q ?? ""] as const,
  career: (id: string) => ["career", id] as const,
  discover: ["discover"] as const,
};

const noRetryOn = (codes: number[]) => (count: number, err: unknown) =>
  !(err instanceof ApiError && codes.includes(err.status)) && count < 2;

export const useMe = () => useQuery({ queryKey: qk.me, queryFn: () => get<Me>("/auth/me"), retry: noRetryOn([401]), staleTime: 60_000 });
export const useVocab = () => useQuery({ queryKey: qk.vocab, queryFn: () => get<Vocab>("/meta/vocab"), staleTime: Infinity });
export const useProfile = () => useQuery({ queryKey: qk.profile, queryFn: () => get<Profile>("/profile") });
export const useAnalysis = () => useQuery({ queryKey: qk.analysis, queryFn: () => get<ProfileAnalysis>("/profile/analysis") });
export const useDashboard = () => useQuery({ queryKey: qk.dashboard, queryFn: () => get<Dashboard>("/dashboard") });
export const useRoadmap = () =>
  useQuery({ queryKey: qk.roadmap, queryFn: () => get<Roadmap>("/roadmap"), retry: noRetryOn([404]) });
export const useGap = (careerId?: string) =>
  useQuery({ queryKey: qk.gap(careerId), queryFn: () => get<GapReport>(`/gap-analysis${careerId ? `?career_id=${careerId}` : ""}`), retry: noRetryOn([400, 404]) });
export const useReadiness = () => useQuery({ queryKey: qk.readiness, queryFn: () => get<Readiness>("/readiness"), retry: noRetryOn([400]) });
export const useProgress = () => useQuery({ queryKey: qk.progress, queryFn: () => get<ProgressData>("/progress") });
export const useRecommendations = () =>
  useQuery({ queryKey: qk.recs, queryFn: () => get<Recommendations>("/recommendations"), retry: noRetryOn([400]), staleTime: 60_000 });
export const useLearning = () => useQuery({ queryKey: qk.learning, queryFn: () => get<any>("/learning"), retry: noRetryOn([404]) });
export const useCareers = (category?: string, q?: string) =>
  useQuery({
    queryKey: qk.careers(category, q),
    queryFn: () => get<{ total: number; items: CareerCard[] }>(`/careers?${new URLSearchParams({ ...(category ? { category } : {}), ...(q ? { q } : {}) })}`),
    staleTime: 5 * 60_000,
  });
export const useCategories = () =>
  useQuery({ queryKey: ["categories"], queryFn: () => get<{ id: string; label: string; count: number; careers: string[] }[]>("/careers/categories"), staleTime: Infinity });
export const useCareer = (id: string) => useQuery({ queryKey: qk.career(id), queryFn: () => get<CareerDetail>(`/careers/${id}`), enabled: !!id });

export const useDiscover = () =>
  useQuery({
    queryKey: qk.discover,
    queryFn: () => post<{ intro: string; matches: CareerMatch[]; profile: ProfileAnalysis; trace: { agent: string; ms: number }[]; research: any; ai_enriched: boolean; principle: string }>("/career/discover"),
    staleTime: 5 * 60_000,
  });

/** Invalidate everything derived from the profile/roadmap after an adaptive change. */
export function useInvalidatePlan() {
  const qc = useQueryClient();
  return () =>
    Promise.all(
      [qk.roadmap, qk.dashboard, qk.progress, qk.readiness, qk.learning, qk.recs, qk.profile, qk.analysis, ["gap"]].map((k) =>
        qc.invalidateQueries({ queryKey: k as readonly unknown[] }),
      ),
    );
}

export function useSelectCareer() {
  const invalidate = useInvalidatePlan();
  return useMutation({
    mutationFn: (career_id: string) => post("/career/select", { career_id }),
    onSuccess: () => invalidate(),
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useGenerateRoadmap() {
  const qc = useQueryClient();
  const invalidate = useInvalidatePlan();
  return useMutation({
    mutationFn: (body: { career_id?: string; hours_per_week?: number }) => post<Roadmap>("/roadmap/generate", body),
    onSuccess: (data) => {
      qc.setQueryData(qk.roadmap, data);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useUpdateStep() {
  const qc = useQueryClient();
  const invalidate = useInvalidatePlan();
  return useMutation({
    mutationFn: ({ id, status, evidence_url }: { id: string; status: string; evidence_url?: string }) =>
      patch<Roadmap>(`/roadmap/steps/${id}`, { status, ...(evidence_url ? { evidence_url } : {}) }),
    onSuccess: (data) => {
      qc.setQueryData(qk.roadmap, data);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });
}

export function useAdjustRoadmap() {
  const qc = useQueryClient();
  const invalidate = useInvalidatePlan();
  return useMutation({
    mutationFn: (body: { hours_per_week?: number; known_skills?: string[] }) => post<Roadmap & { applied_known: string[] }>("/roadmap/adjust", body),
    onSuccess: (data) => {
      qc.setQueryData(qk.roadmap, data);
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });
}
