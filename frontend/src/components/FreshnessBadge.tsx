import React from "react";
import { Badge } from "@/components/ui/badge";

interface FreshnessBadgeProps {
  fetchedAt: string;
  ageMinutes: number;
  source: "live-polled" | "mock";
}

export const FreshnessBadge: React.FC<FreshnessBadgeProps> = ({
  fetchedAt,
  ageMinutes,
  source,
}) => {
  const date = new Date(fetchedAt);
  
  // Format HH:MM
  const hhMm = date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  // Format DD Mon
  const ddMon = date.toLocaleDateString([], {
    day: "2-digit",
    month: "short",
  });

  let dotColorClass = "bg-zinc-500";

  if (source === "live-polled") {
    if (ageMinutes < 10) {
      dotColorClass = "bg-emerald-500 animate-pulse";
    } else if (ageMinutes <= 30) {
      dotColorClass = "bg-amber-500";
    } else {
      dotColorClass = "bg-red-500";
    }
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant="outline" className="px-3 py-1 flex items-center gap-2 border-zinc-800 bg-zinc-950 text-zinc-300 font-normal">
        <span className={`h-2 w-2 rounded-full ${dotColorClass}`} />
        <span>
          {source === "mock" ? "Mock Data" : `Data as of ${hhMm}, ${ddMon}`}
        </span>
        <span className="text-zinc-500 text-xs">
          ({source === "mock" ? "fallback" : `${Math.round(ageMinutes)}m ago`})
        </span>
      </Badge>
    </div>
  );
};
export default FreshnessBadge;
