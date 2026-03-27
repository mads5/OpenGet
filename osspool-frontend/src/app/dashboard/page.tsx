"use client";

import { useEffect, useState, useMemo } from "react";
import { createClient } from "@/lib/supabase/client";
import { getEarnings } from "@/lib/api";
import { EarningsCard } from "@/components/dashboard/earnings-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Payout } from "@/types";
import type { User } from "@supabase/supabase-js";

interface EarningsData {
  total_earned_cents: number;
  pending_cents: number;
  payouts: Payout[];
}

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [earnings, setEarnings] = useState<EarningsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [earningsError, setEarningsError] = useState<string | null>(null);
  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    supabase.auth.getUser().then(async ({ data }) => {
      if (!data.user) {
        setLoading(false);
        return;
      }
      setUser(data.user);
      try {
        const earningsData = await getEarnings(data.user.id);
        setEarnings(earningsData);
      } catch (err) {
        setEarningsError(err instanceof Error ? err.message : "Failed to load earnings");
      }
      setLoading(false);
    });
  }, [supabase]);

  if (loading) {
    return (
      <div className="container py-20 flex justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container py-20 text-center">
        <h2 className="text-2xl font-bold mb-4">Sign in to view your dashboard</h2>
        <p className="text-muted-foreground mb-6">
          Connect your GitHub account to see your maintainer earnings and manage payouts.
        </p>
        <Button
          onClick={() =>
            supabase.auth.signInWithOAuth({
              provider: "github",
              options: { redirectTo: `${window.location.origin}/api/auth/callback?next=/dashboard` },
            })
          }
        >
          Sign in with GitHub
        </Button>
      </div>
    );
  }

  return (
    <div className="container py-8">
      <div className="flex items-center gap-4 mb-8">
        {user.user_metadata?.avatar_url && (
          <img
            src={user.user_metadata.avatar_url}
            alt="Avatar"
            className="h-12 w-12 rounded-full"
          />
        )}
        <div>
          <h1 className="text-2xl font-bold">
            {user.user_metadata?.full_name || user.user_metadata?.user_name}
          </h1>
          <p className="text-muted-foreground">Maintainer Dashboard</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          {earningsError && (
            <div className="text-destructive text-sm mb-4">{earningsError}</div>
          )}
          {earnings ? (
            <EarningsCard
              totalEarned={earnings.total_earned_cents}
              pending={earnings.pending_cents}
              payouts={earnings.payouts}
            />
          ) : !earningsError ? (
            <Card>
              <CardHeader>
                <CardTitle>No Earnings Yet</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Register your open-source projects to start receiving funding from the community.
                </p>
              </CardContent>
            </Card>
          ) : null}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Stripe Connect</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Connect your Stripe account to receive payouts directly.
              </p>
              <Button variant="outline" className="w-full">
                Connect Stripe Account
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Links</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <a href="/leaderboard" className="block text-sm text-primary hover:underline">
                View Leaderboard
              </a>
              <a
                href={`https://github.com/${user.user_metadata?.user_name}`}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-sm text-primary hover:underline"
              >
                Your GitHub Profile
              </a>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
