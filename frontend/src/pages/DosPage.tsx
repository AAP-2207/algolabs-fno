import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Cpu } from "lucide-react";

export const DosPage: React.FC = () => {
  return (
    <div className="flex-1 flex flex-col bg-zinc-950 text-zinc-100 p-8 overflow-y-auto">
      <div className="max-w-4xl w-full mx-auto space-y-6">
        <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
          <Cpu className="h-6 w-6 text-zinc-400" />
          <h2 className="text-xl font-bold tracking-tight">DOS Strategy Engine</h2>
        </div>
        
        <Card className="bg-zinc-900/40 border-zinc-850">
          <CardHeader>
            <CardTitle className="text-sm font-semibold uppercase text-zinc-400 tracking-wider">
              Module Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-zinc-300">
              The Daily Option Seller (DOS) strategy engine handles order configuration, risk profiling, execution simulation, and backtesting for short option positions.
            </p>
            <div className="rounded-lg bg-zinc-950 p-4 border border-zinc-800 border-dashed text-center">
              <span className="text-xs text-zinc-500 font-mono">
                [Phase 7 / 8] Daily Option Seller automation and broker routing simulation. Coming soon.
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
export default DosPage;
