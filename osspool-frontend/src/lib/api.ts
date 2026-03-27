import { createClient } from "@/lib/supabase/client";
import { getSeedRankings, getSeedProject, SEED_PROJECTS, SEED_POOL } from "@/lib/seed-data";
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

async function querySupabase<T>(table: string, query: string): Promise<T | null> {
  try {
    const supabase = createClient();
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!url || !key) return null;

    const res = await fetch(`${url}/rest/v1/${table}?${query}`, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Accept: "application/json",
      },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function getLeaderboard(
  period: string = "weekly",
  page: number = 1,
  perPage: number = 50
): Promise<LeaderboardResponse> {
  const offset = (page - 1) * perPage;
  const supabaseData = await querySupabase<any[]>(
    "rankings",
    `select=*&period=eq.${period}&order=rank.asc&offset=${offset}&limit=${perPage}`
  );

  if (supabaseData && supabaseData.length > 0) {
    return {
      rankings: supabaseData,
      period: period as LeaderboardResponse["period"],
      total: supabaseData.length,
      page,
      per_page: perPage,
      computed_at: supabaseData[0]?.computed_at ?? null,
    };
  }

  try {
    return await fetchAPI<LeaderboardResponse>(
      `/rankings/leaderboard?period=${period}&page=${page}&per_page=${perPage}`
    );
  } catch {
    // Fall back to seed data
  }

  const rankings = getSeedRankings(period);
  return {
    rankings: rankings.slice(offset, offset + perPage),
    period: period as LeaderboardResponse["period"],
    total: rankings.length,
    page,
    per_page: perPage,
    computed_at: new Date().toISOString(),
  };
}

export async function getProject(id: string): Promise<Project> {
  const supabaseData = await querySupabase<any[]>(
    "projects",
    `select=*&id=eq.${id}&limit=1`
  );
  if (supabaseData && supabaseData.length > 0) return supabaseData[0];

  try {
    return await fetchAPI<Project>(`/projects/${id}`);
  } catch {
    // Fall back to seed data
  }

  const seed = getSeedProject(id);
  if (seed) return seed;
  throw new Error("Project not found");
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

  try {
    return await fetchAPI(`/projects?${searchParams}`);
  } catch {
    return { projects: SEED_PROJECTS, total: SEED_PROJECTS.length, page: 1, per_page: 20 };
  }
}

export async function getPool(id: string): Promise<Pool> {
  const supabaseData = await querySupabase<any[]>("money_pools", `select=*&id=eq.${id}&limit=1`);
  if (supabaseData && supabaseData.length > 0) return supabaseData[0];

  try {
    return await fetchAPI<Pool>(`/pools/${id}`);
  } catch {
    return SEED_POOL;
  }
}

export async function listPools(status?: string) {
  const query = status ? `select=*&status=eq.${status}&order=created_at.desc` : "select=*&order=created_at.desc";
  const supabaseData = await querySupabase<any[]>("money_pools", query);
  if (supabaseData && supabaseData.length > 0) return { pools: supabaseData, total: supabaseData.length };

  try {
    const params = status ? `?status=${status}` : "";
    return await fetchAPI<{ pools: Pool[]; total: number }>(`/pools${params}`);
  } catch {
    return { pools: [SEED_POOL], total: 1 };
  }
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
