"use client";

import { useEffect, useState } from "react";
import { getLeaderboard } from "@/lib/api";
import { LeaderboardTable } from "@/components/leaderboard/leaderboard-table";
import { PeriodToggle } from "@/components/leaderboard/period-toggle";
import { TimePeriod, LeaderboardResponse } from "@/types";

export default function LeaderboardPage() {
  const [period, setPeriod] = useState<TimePeriod>("weekly");
  const [data, setData] = useState<LeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getLeaderboard(period)
      .then((res) => setData(res as LeaderboardResponse))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="container py-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold">Leaderboard</h1>
          <p className="text-muted-foreground mt-1">
            Projects ranked by real-world impact metrics
          </p>
        </div>
        <PeriodToggle value={period} onChange={setPeriod} />
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      )}

      {error && (
        <div className="text-center py-12 text-destructive">
          Failed to load leaderboard: {error}
        </div>
      )}

      {data && !loading && (
        <div id="donate">
          <LeaderboardTable rankings={data.rankings} />
          {data.computed_at && (
            <p className="text-xs text-muted-foreground mt-4 text-right">
              Last computed: {new Date(data.computed_at).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
