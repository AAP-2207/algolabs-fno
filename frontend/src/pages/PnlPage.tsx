import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PieChart } from "lucide-react";

export const PnlPage: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col bg-zinc-950 text-zinc-100 p-8 overflow-y-auto">
      <div className="max-w-4xl w-full mx-auto space-y-6">
        <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
          <PieChart className="h-6 w-6 text-zinc-400" />
          <h2 className="text-xl font-bold tracking-tight">P&L Decomposer</h2>
        </div>
        
        <Card className="bg-zinc-900/40 border-zinc-850">
          <CardHeader>
            <CardTitle className="text-sm font-semibold uppercase text-zinc-400 tracking-wider">
              Module Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-zinc-300">
              The P&L Decomposer isolates portfolio gains and losses attributable to change in underlying price (Delta/Gamma P&L), time decay (Theta P&L), and volatility changes (Vega P&L).
            </p>
            <div className="rounded-lg bg-zinc-950 p-4 border border-zinc-800 border-dashed text-center">
              <span className="text-xs text-zinc-500 font-mono">
                [Phase 6 / 8] Greeks Attribution and Portfolio P&L Decomposition Engine. Coming soon.
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
export default PnlPage;
