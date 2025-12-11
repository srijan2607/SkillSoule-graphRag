/**
 * Types for query responses and network insights
 */

export interface SkillPathResult {
  from_skill: string;
  to_skill: string;
  path: string[];
  total_cost: number;
  closeness: number;
}

export interface SimilarJobResult {
  job_id: string;
  job_title: string;
  company?: string;
  jaccard_score: number;
  shared_skills: string[];
}

export interface TopSkillResult {
  skill_name: string;
  canonical_name: string;
  centrality: number;
  demand_count: number;
}

export interface NetworkInsights {
  skill_paths: SkillPathResult[];
  similar_jobs: SimilarJobResult[];
  top_skills: TopSkillResult[];
  transition_feasibility?: number;
  graph_stats?: Record<string, any>;
}

export interface QueryResponse {
  query: string;
  response: string;
  sources: any[];
  processing_time_ms: number;
  metadata: Record<string, any>;
  network_insights?: NetworkInsights | null;
}
