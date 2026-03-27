import type { RankingEntry, Project, Pool } from "@/types";

export const SEED_PROJECTS: Project[] = [
  {
    id: "p-react", github_url: "https://github.com/facebook/react", name: "React",
    description: "The library for web and native user interfaces", language: "JavaScript",
    owner_github_id: "facebook", stars: 231000, forks: 47200, watchers: 6700, open_issues: 920,
    commit_frequency: 18.4, dependents_count: 92000, download_count: 24000000, issue_close_rate: 0.87,
    stars_growth_rate: 320, last_commit_at: "2026-03-26T10:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-next", github_url: "https://github.com/vercel/next.js", name: "Next.js",
    description: "The React Framework for the Web", language: "JavaScript",
    owner_github_id: "vercel", stars: 128000, forks: 27400, watchers: 1400, open_issues: 3200,
    commit_frequency: 32.1, dependents_count: 45000, download_count: 8500000, issue_close_rate: 0.72,
    stars_growth_rate: 210, last_commit_at: "2026-03-27T08:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-vue", github_url: "https://github.com/vuejs/core", name: "Vue.js",
    description: "The Progressive JavaScript Framework", language: "TypeScript",
    owner_github_id: "vuejs", stars: 48000, forks: 8300, watchers: 580, open_issues: 620,
    commit_frequency: 12.8, dependents_count: 38000, download_count: 5200000, issue_close_rate: 0.91,
    stars_growth_rate: 95, last_commit_at: "2026-03-25T14:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-svelte", github_url: "https://github.com/sveltejs/svelte", name: "Svelte",
    description: "Cybernetically enhanced web apps", language: "JavaScript",
    owner_github_id: "sveltejs", stars: 81000, forks: 4300, watchers: 850, open_issues: 310,
    commit_frequency: 14.2, dependents_count: 12000, download_count: 2800000, issue_close_rate: 0.89,
    stars_growth_rate: 140, last_commit_at: "2026-03-26T16:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-tailwind", github_url: "https://github.com/tailwindlabs/tailwindcss", name: "Tailwind CSS",
    description: "A utility-first CSS framework", language: "TypeScript",
    owner_github_id: "tailwindlabs", stars: 85000, forks: 4300, watchers: 580, open_issues: 95,
    commit_frequency: 8.5, dependents_count: 52000, download_count: 12000000, issue_close_rate: 0.95,
    stars_growth_rate: 180, last_commit_at: "2026-03-24T09:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-pytorch", github_url: "https://github.com/pytorch/pytorch", name: "PyTorch",
    description: "Tensors and dynamic neural networks in Python with strong GPU acceleration", language: "Python",
    owner_github_id: "pytorch", stars: 86000, forks: 23000, watchers: 1600, open_issues: 14000,
    commit_frequency: 95.2, dependents_count: 28000, download_count: 9500000, issue_close_rate: 0.68,
    stars_growth_rate: 250, last_commit_at: "2026-03-27T07:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-tensorflow", github_url: "https://github.com/tensorflow/tensorflow", name: "TensorFlow",
    description: "An Open Source Machine Learning Framework for Everyone", language: "C++",
    owner_github_id: "tensorflow", stars: 188000, forks: 74200, watchers: 7900, open_issues: 2400,
    commit_frequency: 42.8, dependents_count: 35000, download_count: 7200000, issue_close_rate: 0.74,
    stars_growth_rate: 110, last_commit_at: "2026-03-26T22:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-fastapi", github_url: "https://github.com/fastapi/fastapi", name: "FastAPI",
    description: "High performance, easy to learn, fast to code, ready for production", language: "Python",
    owner_github_id: "fastapi", stars: 82000, forks: 7100, watchers: 540, open_issues: 480,
    commit_frequency: 6.3, dependents_count: 18000, download_count: 4800000, issue_close_rate: 0.82,
    stars_growth_rate: 190, last_commit_at: "2026-03-25T11:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-django", github_url: "https://github.com/django/django", name: "Django",
    description: "The Web framework for perfectionists with deadlines", language: "Python",
    owner_github_id: "django", stars: 82000, forks: 32000, watchers: 2300, open_issues: 310,
    commit_frequency: 22.4, dependents_count: 62000, download_count: 6800000, issue_close_rate: 0.93,
    stars_growth_rate: 85, last_commit_at: "2026-03-26T15:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-express", github_url: "https://github.com/expressjs/express", name: "Express",
    description: "Fast, unopinionated, minimalist web framework for Node.js", language: "JavaScript",
    owner_github_id: "expressjs", stars: 66000, forks: 17000, watchers: 2100, open_issues: 210,
    commit_frequency: 3.1, dependents_count: 85000, download_count: 32000000, issue_close_rate: 0.78,
    stars_growth_rate: 45, last_commit_at: "2026-03-20T09:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-rust", github_url: "https://github.com/rust-lang/rust", name: "Rust",
    description: "Empowering everyone to build reliable and efficient software", language: "Rust",
    owner_github_id: "rust-lang", stars: 101000, forks: 13000, watchers: 1500, open_issues: 9800,
    commit_frequency: 120.5, dependents_count: 75000, download_count: 3200000, issue_close_rate: 0.81,
    stars_growth_rate: 160, last_commit_at: "2026-03-27T06:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-node", github_url: "https://github.com/nodejs/node", name: "Node.js",
    description: "Node.js JavaScript runtime", language: "JavaScript",
    owner_github_id: "nodejs", stars: 110000, forks: 32000, watchers: 3000, open_issues: 1600,
    commit_frequency: 38.7, dependents_count: 95000, download_count: 45000000, issue_close_rate: 0.76,
    stars_growth_rate: 75, last_commit_at: "2026-03-27T04:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-vite", github_url: "https://github.com/vitejs/vite", name: "Vite",
    description: "Next generation frontend tooling", language: "TypeScript",
    owner_github_id: "vitejs", stars: 70000, forks: 6400, watchers: 440, open_issues: 520,
    commit_frequency: 10.8, dependents_count: 42000, download_count: 15000000, issue_close_rate: 0.85,
    stars_growth_rate: 200, last_commit_at: "2026-03-26T18:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-postgres", github_url: "https://github.com/postgres/postgres", name: "PostgreSQL",
    description: "The world's most advanced open source relational database", language: "C",
    owner_github_id: "postgres", stars: 17000, forks: 4800, watchers: 660, open_issues: 0,
    commit_frequency: 55.3, dependents_count: 120000, download_count: 8000000, issue_close_rate: 0.96,
    stars_growth_rate: 40, last_commit_at: "2026-03-27T02:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-kubernetes", github_url: "https://github.com/kubernetes/kubernetes", name: "Kubernetes",
    description: "Production-Grade Container Orchestration", language: "Go",
    owner_github_id: "kubernetes", stars: 113000, forks: 40000, watchers: 3200, open_issues: 2100,
    commit_frequency: 68.2, dependents_count: 55000, download_count: 3500000, issue_close_rate: 0.88,
    stars_growth_rate: 95, last_commit_at: "2026-03-27T05:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-prisma", github_url: "https://github.com/prisma/prisma", name: "Prisma",
    description: "Next-generation ORM for Node.js & TypeScript", language: "TypeScript",
    owner_github_id: "prisma", stars: 41000, forks: 1600, watchers: 260, open_issues: 3400,
    commit_frequency: 15.6, dependents_count: 22000, download_count: 6200000, issue_close_rate: 0.71,
    stars_growth_rate: 110, last_commit_at: "2026-03-26T20:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-typescript", github_url: "https://github.com/microsoft/TypeScript", name: "TypeScript",
    description: "TypeScript is a superset of JavaScript that compiles to clean JavaScript output", language: "TypeScript",
    owner_github_id: "microsoft", stars: 103000, forks: 12500, watchers: 2100, open_issues: 5800,
    commit_frequency: 28.9, dependents_count: 110000, download_count: 55000000, issue_close_rate: 0.79,
    stars_growth_rate: 120, last_commit_at: "2026-03-27T03:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-lodash", github_url: "https://github.com/lodash/lodash", name: "Lodash",
    description: "A modern JavaScript utility library delivering modularity, performance & extras", language: "JavaScript",
    owner_github_id: "lodash", stars: 60000, forks: 7100, watchers: 940, open_issues: 75,
    commit_frequency: 0.8, dependents_count: 180000, download_count: 58000000, issue_close_rate: 0.45,
    stars_growth_rate: 10, last_commit_at: "2025-08-10T09:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-eslint", github_url: "https://github.com/eslint/eslint", name: "ESLint",
    description: "Find and fix problems in your JavaScript code", language: "JavaScript",
    owner_github_id: "eslint", stars: 25500, forks: 4600, watchers: 350, open_issues: 110,
    commit_frequency: 8.4, dependents_count: 95000, download_count: 42000000, issue_close_rate: 0.92,
    stars_growth_rate: 35, last_commit_at: "2026-03-25T17:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
  {
    id: "p-huggingface", github_url: "https://github.com/huggingface/transformers", name: "Transformers",
    description: "State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX", language: "Python",
    owner_github_id: "huggingface", stars: 140000, forks: 28000, watchers: 1200, open_issues: 1400,
    commit_frequency: 52.1, dependents_count: 15000, download_count: 12000000, issue_close_rate: 0.83,
    stars_growth_rate: 380, last_commit_at: "2026-03-27T09:00:00Z", is_active: true,
    created_at: "2024-01-01T00:00:00Z", updated_at: "2026-03-27T00:00:00Z",
  },
];

function computeScore(p: Project): { total: number; breakdown: RankingEntry["breakdown"] } {
  const maxDep = 180000, maxDl = 58000000, maxCommit = 120.5, maxClose = 0.96, maxGrowth = 380;
  const depScore = (p.dependents_count / maxDep) * 30;
  const dlScore = (p.download_count / maxDl) * 25;
  const commitScore = (p.commit_frequency / maxCommit) * 20;
  const closeScore = (p.issue_close_rate / maxClose) * 15;
  const growthScore = (p.stars_growth_rate / maxGrowth) * 10;
  return {
    total: depScore + dlScore + commitScore + closeScore + growthScore,
    breakdown: {
      dependents_score: Math.round(depScore * 10) / 10,
      download_velocity_score: Math.round(dlScore * 10) / 10,
      commit_recency_score: Math.round(commitScore * 10) / 10,
      issue_close_rate_score: Math.round(closeScore * 10) / 10,
      stars_growth_score: Math.round(growthScore * 10) / 10,
      time_decay_factor: 1.0,
    },
  };
}

export function getSeedRankings(period: string): RankingEntry[] {
  return SEED_PROJECTS
    .map((p) => {
      const { total, breakdown } = computeScore(p);
      return { total, breakdown, project: p };
    })
    .sort((a, b) => b.total - a.total)
    .map(({ total, breakdown, project }, i) => ({
      id: `r-${project.id}`,
      project_id: project.id,
      project_name: project.name,
      github_url: project.github_url,
      rank: i + 1,
      total_score: Math.round(total * 10) / 10,
      breakdown,
      period: period as RankingEntry["period"],
      computed_at: new Date().toISOString(),
    }));
}

export function getSeedProject(id: string): Project | undefined {
  return SEED_PROJECTS.find((p) => p.id === id);
}

export const SEED_POOL: Pool = {
  id: "pool-q1-2026",
  name: "Q1 2026 Funding Round",
  description: "Quarterly quadratic funding pool for critical open-source infrastructure",
  target_amount_cents: 5000000,
  current_amount_cents: 3250000,
  matched_pool_cents: 1875000,
  status: "active",
  start_date: "2026-01-01T00:00:00Z",
  end_date: "2026-03-31T23:59:59Z",
  match_ratio: 1.5,
  donor_count: 1842,
  project_count: 20,
  created_at: "2026-01-01T00:00:00Z",
};
