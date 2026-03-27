"use client";

import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCurrency } from "@/lib/utils";
import { Pool } from "@/types";

interface PoolProgressProps {
  pool: Pool;
}

export function PoolProgress({ pool }: PoolProgressProps) {
  const totalRaised = pool.current_amount_cents + pool.matched_pool_cents;
  const percentage = Math.min((totalRaised / pool.target_amount_cents) * 100, 100);
  const daysLeft = Math.max(
    0,
    Math.ceil(
      (new Date(pool.end_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
    )
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{pool.name}</CardTitle>
        {pool.description && (
          <p className="text-sm text-muted-foreground">{pool.description}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="flex justify-between text-sm mb-2">
            <span className="font-medium">{formatCurrency(totalRaised)} raised</span>
            <span className="text-muted-foreground">
              of {formatCurrency(pool.target_amount_cents)}
            </span>
          </div>
          <Progress value={percentage} className="h-3" />
          <div className="flex justify-between text-xs text-muted-foreground mt-2">
            <span>{percentage.toFixed(1)}% funded</span>
            <span>{pool.match_ratio}x matching</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 pt-2 border-t">
          <div className="text-center">
            <div className="text-lg font-bold">{pool.donor_count}</div>
            <div className="text-xs text-muted-foreground">Donors</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold">{pool.project_count}</div>
            <div className="text-xs text-muted-foreground">Projects</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold">{daysLeft}</div>
            <div className="text-xs text-muted-foreground">Days Left</div>
          </div>
        </div>

        <div className="pt-2 border-t">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Direct donations</span>
            <span>{formatCurrency(pool.current_amount_cents)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Matched funding</span>
            <span className="text-primary font-medium">
              +{formatCurrency(pool.matched_pool_cents)}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
