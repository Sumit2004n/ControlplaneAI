"use client";
import {
  Activity, BarChart3, BookOpen, ClipboardCheck, FileSearch, LayoutDashboard,
  ListChecks, ScrollText, Settings, ShieldCheck, SlidersHorizontal, Zap,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analyzer", label: "Analyzer", icon: Zap },
  { href: "/live-monitor", label: "Live Monitor", icon: Activity },
  { href: "/interactions", label: "Interactions", icon: FileSearch },
  { href: "/review-queue", label: "Review Queue", icon: ClipboardCheck },
  { href: "/policies", label: "Policies", icon: SlidersHorizontal },
  { href: "/simulator", label: "Policy Simulator", icon: ListChecks },
  { href: "/knowledge-base", label: "Knowledge Base", icon: BookOpen },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/audit-logs", label: "Audit Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-2.5 border-b border-slate-200 px-5 py-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600">
          <ShieldCheck className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="text-sm font-bold leading-tight text-slate-900">ControlPlane.ai</div>
          <div className="text-[11px] leading-tight text-slate-500">Enterprise AI Governance</div>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link key={href} href={href}
              className={clsx(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition",
                active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900",
              )}>
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-200 p-4 text-[11px] leading-relaxed text-slate-400">
        Round 2 Prototype<br />Accenture Innovation Challenge
      </div>
    </aside>
  );
}
