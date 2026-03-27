export type TimePeriod = "daily" | "weekly" | "monthly" | "yearly" | "all_time";

export interface RankingScoreBreakdown {
  dependents_score: number;
  download_velocity_score: number;
  commit_recency_score: number;
  issue_close_rate_score: number;
  stars_growth_score: number;
  time_decay_factor: number;
}

export interface RankingEntry {
  id: string;
  project_id: string;
  project_name: string;
  github_url: string;
  rank: number;
  total_score: number;
  breakdown: RankingScoreBreakdown;
  period: TimePeriod;
  computed_at: string;
}

export interface LeaderboardResponse {
  rankings: RankingEntry[];
  period: TimePeriod;
  total: number;
  page: number;
  per_page: number;
  computed_at: string | null;
}

export interface Project {
  id: string;
  github_url: string;
  name: string;
  description: string | null;
  language: string | null;
  owner_github_id: string;
  stars: number;
  forks: number;
  watchers: number;
  open_issues: number;
  commit_frequency: number;
  dependents_count: number;
  download_count: number;
  issue_close_rate: number;
  stars_growth_rate: number;
  last_commit_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Pool {
  id: string;
  name: string;
  description: string | null;
  target_amount_cents: number;
  current_amount_cents: number;
  matched_pool_cents: number;
  status: "active" | "distributing" | "completed" | "cancelled";
  start_date: string;
  end_date: string;
  match_ratio: number;
  donor_count: number;
  project_count: number;
  created_at: string;
}

export interface Donation {
  id: string;
  pool_id: string;
  project_id: string;
  donor_id: string;
  amount_cents: number;
  matched_amount_cents: number;
  created_at: string;
}

export interface Payout {
  id: string;
  pool_id: string;
  project_id: string;
  recipient_id: string;
  amount_cents: number;
  matched_amount_cents: number;
  total_payout_cents: number;
  status: "pending" | "processing" | "completed" | "failed";
  stripe_transfer_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface User {
  id: string;
  github_id: string;
  github_username: string;
  avatar_url: string | null;
  email: string | null;
  stripe_connect_account_id: string | null;
  is_maintainer: boolean;
  created_at: string;
}
