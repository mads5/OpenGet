"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatCurrency } from "@/lib/utils";
import { Payout } from "@/types";

interface EarningsCardProps {
  totalEarned: number;
  pending: number;
  payouts: Payout[];
}

export function EarningsCard({ totalEarned, pending, payouts }: EarningsCardProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Earned
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-primary">
              {formatCurrency(totalEarned)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pending Payouts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{formatCurrency(pending)}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Payout History</CardTitle>
        </CardHeader>
        <CardContent>
          {payouts.length === 0 ? (
            <p className="text-muted-foreground text-sm">No payouts yet</p>
          ) : (
            <div className="space-y-3">
              {payouts.map((payout) => (
                <div
                  key={payout.id}
                  className="flex items-center justify-between py-2 border-b last:border-0"
                >
                  <div>
                    <div className="text-sm font-medium">
                      {formatCurrency(payout.total_payout_cents)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {new Date(payout.created_at).toLocaleDateString()}
                      {" · "}
                      {formatCurrency(payout.matched_amount_cents)} matched
                    </div>
                  </div>
                  <Badge
                    variant={
                      payout.status === "completed"
                        ? "default"
                        : payout.status === "failed"
                        ? "destructive"
                        : "secondary"
                    }
                  >
                    {payout.status}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
