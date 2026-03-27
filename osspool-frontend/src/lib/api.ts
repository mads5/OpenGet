import { createClient } from "@/lib/supabase/client";
import type { Repo, Contributor, ContributorDetail, Pool, Donation, Payout, GitHubRepoInfo } from "@/types";

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

// ---- Repos ----

export async function listRepos(page = 1, perPage = 20): Promise<{ repos: Repo[]; total: number }> {
  const sbData = await querySupabase<Repo[]>(
    "repos",
    `select=*&order=stars.desc&offset=${(page - 1) * perPage}&limit=${perPage}`
  );
  if (sbData && sbData.length > 0) return { repos: sbData, total: sbData.length };

  try {
    return await fetchAPI<{ repos: Repo[]; total: number }>(`/repos?page=${page}&per_page=${perPage}`);
  } catch {
    return { repos: [], total: 0 };
  }
}

export async function getRepo(id: string): Promise<Repo> {
  const sbData = await querySupabase<Repo[]>("repos", `select=*&id=eq.${id}&limit=1`);
  if (sbData && sbData.length > 0) return sbData[0];

  return fetchAPI<Repo>(`/repos/${id}`);
}

export async function getRepoContributors(repoId: string) {
  try {
    return await fetchAPI<{ contributors: any[] }>(`/repos/${repoId}/contributors`);
  } catch {
    return { contributors: [] };
  }
}

export async function getMyGithubRepos(): Promise<GitHubRepoInfo[]> {
  return fetchAPI<GitHubRepoInfo[]>("/repos/mine");
}

export async function listRepo(githubUrl: string): Promise<Repo> {
  return fetchAPI<Repo>("/repos", {
    method: "POST",
    body: JSON.stringify({ github_url: githubUrl }),
  });
}

// ---- Contributors ----

export async function listContributors(page = 1, perPage = 50): Promise<{ contributors: Contributor[]; total: number }> {
  const sbData = await querySupabase<Contributor[]>(
    "contributors",
    `select=*&order=total_score.desc&offset=${(page - 1) * perPage}&limit=${perPage}`
  );
  if (sbData && sbData.length > 0) {
    const enriched = sbData.map((c) => ({ ...c, is_registered: c.user_id != null }));
    return { contributors: enriched, total: enriched.length };
  }

  try {
    return await fetchAPI<{ contributors: Contributor[]; total: number }>(`/contributors?page=${page}&per_page=${perPage}`);
  } catch {
    return { contributors: [], total: 0 };
  }
}

export async function getContributor(id: string): Promise<ContributorDetail> {
  return fetchAPI<ContributorDetail>(`/contributors/${id}`);
}

export async function registerContributor(): Promise<Contributor> {
  return fetchAPI<Contributor>("/contributors/register", { method: "POST" });
}

// ---- Pool ----

export async function getActivePool(): Promise<Pool | null> {
  const sbData = await querySupabase<Pool[]>(
    "pool",
    `select=*&status=eq.active&order=created_at.desc&limit=1`
  );
  if (sbData && sbData.length > 0) return sbData[0];

  try {
    return await fetchAPI<Pool | null>("/pool");
  } catch {
    return null;
  }
}

export async function createCheckoutSession(
  amountCents: number,
  message?: string,
  currency?: string,
): Promise<{ checkout_url: string; session_id: string }> {
  return fetchAPI<{ checkout_url: string; session_id: string }>("/pool/create-checkout-session", {
    method: "POST",
    body: JSON.stringify({
      amount_cents: amountCents,
      currency: currency || undefined,
      message,
      success_url: `${window.location.origin}/donate/success`,
      cancel_url: `${window.location.origin}/donate`,
    }),
  });
}

export async function createUpiQr(
  amountPaisa: number,
  message?: string,
): Promise<{ qr_id: string; image_url: string; amount_paisa: number; status: string }> {
  return fetchAPI<{ qr_id: string; image_url: string; amount_paisa: number; status: string }>("/pool/create-upi-qr", {
    method: "POST",
    body: JSON.stringify({ amount_paisa: amountPaisa, message }),
  });
}

export async function checkUpiQrStatus(
  qrId: string,
): Promise<{ qr_id: string; status: string; paid: boolean; payments_count: number }> {
  return fetchAPI<{ qr_id: string; status: string; paid: boolean; payments_count: number }>(`/pool/upi-qr-status/${qrId}`);
}

export async function donate(amountCents: number, message?: string): Promise<Donation> {
  return fetchAPI<Donation>("/pool/donate", {
    method: "POST",
    body: JSON.stringify({ amount_cents: amountCents, message }),
  });
}

// ---- Payouts ----

export async function getEarnings() {
  return fetchAPI<{
    contributor_id: string;
    total_earned_cents: number;
    pending_cents: number;
    payouts: Payout[];
  }>("/payouts/earnings");
}

export async function onboardStripeConnect(userId: string, email: string) {
  return fetchAPI<{ account_id: string; onboarding_url: string }>("/payouts/stripe-connect", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, email }),
  });
}

// ---- Stats (for homepage) ----

export async function getStats(): Promise<{ repos: number; contributors: number; poolCents: number; donors: number }> {
  try {
    const [reposData, contribData, poolData] = await Promise.all([
      querySupabase<{ count: number }[]>("repos", "select=id&limit=0"),
      querySupabase<{ count: number }[]>("contributors", "select=id&limit=0"),
      querySupabase<Pool[]>("pool", "select=*&status=eq.active&order=created_at.desc&limit=1"),
    ]);

    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    let repoCount = 0;
    let contribCount = 0;

    if (url && key) {
      const [rCount, cCount] = await Promise.all([
        fetch(`${url}/rest/v1/repos?select=id`, {
          headers: { apikey: key, Authorization: `Bearer ${key}`, Accept: "application/json", Prefer: "count=exact" },
        }).then(r => parseInt(r.headers.get("content-range")?.split("/")[1] || "0")).catch(() => 0),
        fetch(`${url}/rest/v1/contributors?select=id`, {
          headers: { apikey: key, Authorization: `Bearer ${key}`, Accept: "application/json", Prefer: "count=exact" },
        }).then(r => parseInt(r.headers.get("content-range")?.split("/")[1] || "0")).catch(() => 0),
      ]);
      repoCount = rCount;
      contribCount = cCount;
    }

    const pool = poolData && poolData.length > 0 ? poolData[0] : null;

    return {
      repos: repoCount,
      contributors: contribCount,
      poolCents: pool?.total_amount_cents ?? 0,
      donors: pool?.donor_count ?? 0,
    };
  } catch {
    return { repos: 0, contributors: 0, poolCents: 0, donors: 0 };
  }
}
