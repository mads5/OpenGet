"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TimePeriod } from "@/types";

interface PeriodToggleProps {
  value: TimePeriod;
  onChange: (period: TimePeriod) => void;
}

const PERIODS: { value: TimePeriod; label: string }[] = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
  { value: "all_time", label: "All Time" },
];

export function PeriodToggle({ value, onChange }: PeriodToggleProps) {
  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as TimePeriod)}>
      <TabsList>
        {PERIODS.map((period) => (
          <TabsTrigger key={period.value} value={period.value}>
            {period.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
