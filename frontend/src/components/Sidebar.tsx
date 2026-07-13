import React from "react";
import { NavLink } from "react-router-dom";
import { Layers, Activity, PieChart, Cpu } from "lucide-react";

export const Sidebar: React.FC = () => {
  const menuItems = [
    {
      name: "Option Chain",
      path: "/chain",
      icon: Layers,
      desc: "Live NSE NIFTY Derivatives",
    },
    {
      name: "Greeks & IV",
      path: "/greeks",
      icon: Activity,
      desc: "Option Pricing & Greeks",
    },
    {
      name: "P&L Decomposer",
      path: "/pnl",
      icon: PieChart,
      desc: "Deconstruct Portfolio risk",
    },
    {
      name: "DOS Strategy",
      path: "/dos",
      icon: Cpu,
      desc: "Daily Option Seller Engine",
    },
  ];

  return (
    <aside className="w-64 border-r border-zinc-800 bg-zinc-950 flex flex-col h-screen shrink-0">
      {/* Platform Title */}
      <div className="p-6 border-b border-zinc-800 flex items-center gap-2">
        <div className="h-8 w-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white font-bold text-lg">
          A
        </div>
        <div>
          <h1 className="font-bold text-sm text-zinc-100 tracking-wider">
            ALGOLABS
          </h1>
          <p className="text-zinc-500 text-[10px] uppercase font-semibold">
            Derivatives Desk
          </p>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-start gap-3 px-4 py-3 rounded-lg transition-all duration-200 group ${
                  isActive
                    ? "bg-zinc-900 text-emerald-400 border border-zinc-800"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40 border border-transparent"
                }`
              }
            >
              <Icon className="h-5 w-5 mt-0.5 shrink-0 group-hover:scale-105 transition-transform duration-200" />
              <div className="flex flex-col">
                <span className="text-sm font-medium">{item.name}</span>
                <span className="text-[10px] text-zinc-500 font-normal leading-tight group-hover:text-zinc-400">
                  {item.desc}
                </span>
              </div>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-zinc-850 bg-zinc-950 text-center">
        <p className="text-[10px] text-zinc-600">
          AlgoLabs F&O Platform v1.0.0
        </p>
        <p className="text-[9px] text-zinc-700">Residential poller node active</p>
      </div>
    </aside>
  );
};
export default Sidebar;
