import { createClient } from "@/lib/supabase/client";
import type { LeaderboardResponse, Project, Pool, Payout } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function getAuthHeaders(): Promise<Record<string, string>> {
  try {
    const supabase = createClient();
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) {
      return { Authorization: `Bearer ${data.session.access_token}` };
    }
  } catch {
    // Not authenticated
  }
  return {};
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    const detail = Array.isArray(error.detail)
      ? error.detail.map((d: any) => d.msg || d).join(", ")
      : error.detail || `API error: ${res.status}`;
    throw new Error(detail);
  }

  return res.json();
}

export async function getLeaderboard(
  period: string = "weekly",
  page: number = 1,
  perPage: number = 50
): Promise<LeaderboardResponse> {
  return fetchAPI<LeaderboardResponse>(
    `/rankings/leaderboard?period=${period}&page=${page}&per_page=${perPage}`
  );
}

export async function getProject(id: string): Promise<Project> {
  return fetchAPI<Project>(`/projects/${id}`);
}

export async function listProjects(params?: {
  page?: number;
  language?: string;
  search?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.language) searchParams.set("language", params.language);
  if (params?.search) searchParams.set("search", params.search);
  return fetchAPI(`/projects?${searchParams}`);
}

export async function getPool(id: string): Promise<Pool> {
  return fetchAPI<Pool>(`/pools/${id}`);
}

export async function listPools(status?: string) {
  const params = status ? `?status=${status}` : "";
  return fetchAPI<{ pools: Pool[]; total: number }>(`/pools${params}`);
}

export async function donateToPool(poolId: string, data: {
  project_id: string;
  amount_cents: number;
}) {
  return fetchAPI(`/pools/${poolId}/donate`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getEarnings(userId: string) {
  return fetchAPI<{
    user_id: string;
    total_earned_cents: number;
    pending_cents: number;
    payouts: Payout[];
  }>(`/payouts/earnings/${userId}`);
}
