export type Level = 0 | 1 | 2 | 3;

export interface Me { id: string; email: string; name: string; is_demo: boolean; onboarding_completed: boolean }

export interface Vocab {
  interests: { id: string; label: string }[];
  activities: { id: string; label: string }[];
  work_styles: { id: string; label: string }[];
  skill_groups: Record<"languages" | "ai_data" | "tools", { id: string; name: string }[]>;
  all_skills: { id: string; name: string; category: string }[];
  experience_levels: string[];
  learning_preferences: string[];
}

export interface Evidence { kind: string; title: string; ref_id: string | null }

export interface ProfileAnalysis {
  name: string;
  disclaimer: string;
  domains: { domain: string; label: string; score: number; reasons: string[] }[];
  strong_interests: string[];
  current_strengths: { skill_id: string; name: string; level: number; level_label: string; evidence: Evidence[] }[];
  developing_skills: { skill_id: string; name: string; level: number; level_label: string }[];
  unsure_skills: string[];
  work_preferences: string[];
  summary: string;
  stats: { skills: number; projects: number; certificates: number };
}

export interface Reason { type: string; label: string; detail: string; source: string }

export interface CareerMatch {
  career_id: string; name: string; family: string; summary: string; fit_label: string;
  signals: { interest_fit: number; activity_fit: number; skill_fit: number };
  reasons: Reason[]; why_summary: string; to_explore: string[]; ai_explanation?: string;
}

export interface CareerCard { id: string; name: string; family: string; categories: string[]; summary: string; skill_focus: string }

export interface CareerDetail {
  id: string; name: string; family: string; categories: string[]; summary: string; what_they_do: string;
  responsibilities: string[];
  skills: { skill_id: string; name: string; category: string; importance: string; target_level: number; target_label: string; your_level?: number; your_label?: string }[];
  technologies: string[]; entry_routes: string[]; example_projects: string[];
  project_templates: { id: string; name: string; difficulty: string }[];
  certificates: { id: string; name: string; provider: string }[];
  typical_learning_path: { name: string; skills: string[] }[];
  related: { id: string; name: string; summary: string }[];
  who_might_enjoy: string[]; questions_to_explore: string[];
  skill_focus: string; typical_outputs: string; your_coverage: number | null; is_target: boolean; source_note: string;
}

export interface GapItem {
  skill_id: string; name: string; category: string; importance: "core" | "important" | "useful";
  target_level: number; target_label: string; current_level: number; current_label: string; unsure: boolean;
  status: "strong" | "developing" | "needs_development" | "not_explored"; status_label: string; bar: number; priority: number;
  evidence: Evidence[];
  explanation: null | {
    why_it_matters: string; what_to_learn: string; resources: Resource[]; suggested_practice: string;
    suggested_project: { id: string; name: string } | null; optional_certificate: { id: string; name: string; provider: string } | null;
  };
}

export interface GapReport {
  career_id: string; career_name: string; items: GapItem[]; strengths: string[]; priority_gaps: string[];
  counts: Record<string, number>; note: string;
}

export interface Resource { title: string; provider?: string | null; url?: string | null; type?: string }

export interface RoadmapStep {
  id: string; kind: "skill" | "project" | "milestone"; skill_id: string | null; title: string;
  status: "todo" | "in_progress" | "done" | "skipped"; est_hours: number; from_level: number; target_level: number;
  importance: string; optional: boolean; is_prerequisite: boolean; completed_at: string | null;
  content: { learn?: Resource[]; practice?: string; build?: string; prove?: string; focus?: string; problem?: string; architecture?: string[]; expected_output?: string; why_it_fits?: string };
}

export interface RoadmapPhase {
  index: number; name: string; steps: RoadmapStep[]; covered: { skill_id: string; name: string; reason: string }[];
  est_hours: number; remaining_hours: number; weeks_min: number; weeks_max: number; duration_label: string;
  status: "todo" | "in_progress" | "done" | "covered"; progress: number;
}

export interface Roadmap {
  id: string; career_id: string; career_name: string; version: number; generated_at: string; hours_per_week: number;
  phases: RoadmapPhase[]; carried_over: string[]; switched_from: string | null; adjustments: { at: string; text: string }[];
  total_hours: number; remaining_hours: number; remaining_label: string; skills_total: number; skills_done: number; timeline_note: string;
}

export interface ProjectRec {
  id: string; name: string; difficulty: "beginner" | "intermediate" | "advanced"; problem: string; why_it_fits: string;
  skills_learned: string[]; skill_ids: string[]; technologies: string[]; estimated_hours: number; estimated_time: string;
  architecture: string[]; expected_output: string; portfolio_value: string; suggested_start?: boolean;
  evidence: { gaps_covered: string[]; strengths_used: string[] }; domain_flavor: string | null;
}

export interface CertRec {
  id: string; name: string; provider: string; type: string; level: string; url: string | null;
  verdict: "worth_exploring" | "consider" | "project_first"; why: string;
  evidence: { covers_gaps: string[]; already_demonstrated: string[]; listed_for_career: boolean };
  expected_benefit: string; difficulty: string; time_required: string; notes: string;
}

export interface Recommendations {
  career_id: string; career_name: string;
  certificates: { recommendations: CertRec[]; existing: { name: string; matched_catalog: string | null; demonstrates: string[]; relevant_to_target: string[] }[]; principle: string };
  projects: { projects: ProjectRec[]; suggested_start: string | null };
  learning: LearningItem[];
}

export interface LearningItem {
  skill_id: string; name: string; focus: string; learn: Resource[]; practice: string; build: string; prove: string;
  estimated_hours: number; phase?: string; status?: string; step_id?: string; optional?: boolean;
}

export interface ReadinessEntry { skill_id: string; name: string; importance: string; evidence: string; self_reported_only: boolean }
export interface Readiness {
  career_id: string; career_name: string;
  buckets: { strong: ReadinessEntry[]; developing: ReadinessEntry[]; limited: ReadinessEntry[] };
  next_step: string; self_reported_note: string | null; principle: string;
}

export interface EvidenceItem { id: number; kind: string; label: string; title: string; detail: string | null; url: string | null; skills: string[]; created_at: string }

export interface ProgressData {
  has_roadmap: boolean; career_id?: string; career_name?: string; overall?: number; overall_basis?: string;
  skills?: { done: number; total: number }; projects?: { done: number; total: number }; phases?: { done: number; total: number };
  phase_progress?: { name: string; progress: number; status: string }[];
  next_step?: (RoadmapStep & { phase_name: string }) | null; remaining_label?: string; evidence: EvidenceItem[]; readiness?: Readiness;
}

export interface Dashboard {
  name: string; onboarding_completed: boolean; target: { id: string; name: string } | null; progress?: number | null;
  has_roadmap?: boolean; next_step?: (RoadmapStep & { phase_name: string }) | null;
  recommended_project?: { id: string; name: string; difficulty: string } | null;
  insights?: { skills_to_develop: number; projects_recommended: number; certificates_worth_exploring: number };
  readiness_next_step?: string; phase_progress?: { name: string; progress: number; status: string }[];
  recent_evidence?: EvidenceItem[]; remaining_label?: string;
}

export interface Profile {
  user: { id: string; email: string; name: string; is_demo: boolean; auth_provider: string };
  onboarding_completed: boolean; interests: string[];
  skills: { skill_id: string; name: string; level: number; unsure: boolean; source: string }[];
  activities: string[]; work_styles: string[]; subjects: string[];
  education: { level?: string; degree?: string; field?: string }; experience_level: string | null;
  career_goals: string | null; learning_preferences: string[]; hours_per_week: number;
  target_career_id: string | null; target_career_name: string | null;
  certificates: UserCertificate[]; projects: UserProject[];
}

export interface UserCertificate {
  id: string; name: string; issuer: string | null; completed_on: string | null; catalog_id: string | null; has_file: boolean;
  analysis: { certificate?: string; provider?: string; skills_covered?: { skill_id: string; name: string }[]; topics?: string[]; level?: string; demonstrates?: string; matched_catalog?: boolean; type?: string };
}

export interface UserProject {
  id: string; name: string; description: string; technologies: string[]; role: string | null; github_url: string | null; demo_url: string | null;
  status: string; source: string;
  analysis: { skills_demonstrated?: { skill_id: string; name: string }[]; difficulty?: string; domain_labels?: string[]; career_relevance?: { career_id: string; name: string; matched_skills: string[] }[] };
}

export interface Source { n: number; id: string; title: string; type: string; source: string; url: string | null; snippet: string }
