"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Zap, TrendingUp, Brain, Rocket } from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", Icon: BarChart3 },
  { href: "/predict", label: "Classify", Icon: Zap },
  { href: "/monitor", label: "Monitor", Icon: TrendingUp },
  { href: "/training", label: "Training", Icon: Brain },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 backdrop-blur-md border-b border-slate-700/50 bg-gradient-to-r from-slate-900/80 via-slate-900/80 to-purple-900/40">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="text-3xl group-hover:scale-110 transition-transform">
            <Rocket className="w-8 h-8 text-cyan-400" />
          </div>
          <div>
            <div className="font-bold text-xl bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              AI-News
            </div>
            <div className="text-xs text-gray-400">Monitor</div>
          </div>
        </Link>

        <div className="flex gap-1 ml-12">
          {links.map((l) => {
            const isActive = pathname === l.href;
            const Icon = l.Icon;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  isActive
                    ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/50"
                    : "text-gray-300 hover:text-white hover:bg-slate-800/50"
                }`}
              >
                <Icon className="w-4 h-4" />
                {l.label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
          <span className="text-xs text-gray-400">Live</span>
        </div>
      </div>
    </nav>
  );
}
