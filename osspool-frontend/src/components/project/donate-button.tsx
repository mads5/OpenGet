"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { donateToPool } from "@/lib/api";

interface DonateButtonProps {
  projectId: string;
  poolId?: string;
}

const AMOUNTS = [500, 1000, 2500, 5000, 10000];

export function DonateButton({ projectId, poolId }: DonateButtonProps) {
  const [selectedAmount, setSelectedAmount] = useState(1000);
  const [loading, setLoading] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleDonate = async () => {
    if (!poolId) return;
    setLoading(true);
    setError(null);
    try {
      await donateToPool(poolId, {
        project_id: projectId,
        amount_cents: selectedAmount,
      });
      setSuccess(true);
      setShowPicker(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Donation failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="text-center space-y-2">
        <p className="text-sm font-medium text-primary">Thank you for your donation!</p>
        <Button variant="outline" size="sm" onClick={() => { setSuccess(false); setShowPicker(false); }}>
          Donate again
        </Button>
      </div>
    );
  }

  if (!showPicker) {
    return (
      <Button size="lg" className="w-full" onClick={() => setShowPicker(true)}>
        Fund This Project
      </Button>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-5 gap-2">
        {AMOUNTS.map((amount) => (
          <button
            key={amount}
            onClick={() => setSelectedAmount(amount)}
            className={`py-2 px-1 rounded-md text-sm font-medium transition-colors ${
              selectedAmount === amount
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80"
            }`}
          >
            ${amount / 100}
          </button>
        ))}
      </div>
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
      <Button
        size="lg"
        className="w-full"
        onClick={handleDonate}
        disabled={loading}
      >
        {loading ? "Processing..." : `Donate $${selectedAmount / 100}`}
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="w-full"
        onClick={() => { setShowPicker(false); setError(null); }}
      >
        Cancel
      </Button>
    </div>
  );
}
