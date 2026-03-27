"use client";

import Link from "next/link";
import { RankingEntry } from "@/types";
import { formatScore } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

interface LeaderboardTableProps {
  rankings: RankingEntry[];
}

export function LeaderboardTable({ rankings }: LeaderboardTableProps) {
  if (!rankings.length) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No rankings available for this period yet.
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="w-full">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-4 py-3 text-sm font-medium">Rank</th>
            <th className="text-left px-4 py-3 text-sm font-medium">Project</th>
            <th className="text-right px-4 py-3 text-sm font-medium hidden md:table-cell">Dependents</th>
            <th className="text-right px-4 py-3 text-sm font-medium hidden md:table-cell">Downloads</th>
            <th className="text-right px-4 py-3 text-sm font-medium hidden sm:table-cell">Commit Recency</th>
            <th className="text-right px-4 py-3 text-sm font-medium hidden lg:table-cell">Issue Close Rate</th>
            <th className="text-right px-4 py-3 text-sm font-medium hidden lg:table-cell">Stars Growth</th>
            <th className="text-right px-4 py-3 text-sm font-medium">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {rankings.map((entry) => (
            <tr key={entry.id} className="hover:bg-muted/30 transition-colors">
              <td className="px-4 py-3">
                <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                  entry.rank <= 3 ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                }`}>
                  {entry.rank}
                </span>
              </td>
              <td className="px-4 py-3">
                <Link
                  href={`/project/${entry.project_id}`}
                  className="font-medium hover:text-primary transition-colors"
                >
                  {entry.project_name}
                </Link>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {entry.github_url.replace("https://github.com/", "")}
                </div>
              </td>
              <td className="text-right px-4 py-3 text-sm hidden md:table-cell">
                {formatScore(entry.breakdown.dependents_score)}
              </td>
              <td className="text-right px-4 py-3 text-sm hidden md:table-cell">
                {formatScore(entry.breakdown.download_velocity_score)}
              </td>
              <td className="text-right px-4 py-3 text-sm hidden sm:table-cell">
                {formatScore(entry.breakdown.commit_recency_score)}
              </td>
              <td className="text-right px-4 py-3 text-sm hidden lg:table-cell">
                {formatScore(entry.breakdown.issue_close_rate_score)}
              </td>
              <td className="text-right px-4 py-3 text-sm hidden lg:table-cell">
                {formatScore(entry.breakdown.stars_growth_score)}
              </td>
              <td className="text-right px-4 py-3">
                <Badge variant={entry.rank <= 10 ? "default" : "secondary"}>
                  {formatScore(entry.total_score)}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
