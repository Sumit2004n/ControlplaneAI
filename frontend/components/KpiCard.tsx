import type { LucideIcon } from "lucide-react";

export default function KpiCard({ label, value, sub, icon: Icon, tone = "default" }: {
  label: string;
  value: string | number;
  sub?: string;
  icon: LucideIcon;
  tone?: "default" | "red" | "orange" | "violet" | "green";
}) {
  const tones: Record<string, string> = {
    default: "bg-brand-50 text-brand-600",
    red: "bg-red-50 text-red-600",
    orange: "bg-orange-50 text-orange-600",
    violet: "bg-violet-50 text-violet-600",
    green: "bg-emerald-50 text-emerald-600",
  };
  return (
    <div className="card flex items-center gap-3 p-4">
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${tones[tone]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <div className="truncate text-xs font-medium text-slate-500">{label}</div>
        <div className="text-xl font-bold tabular-nums text-slate-900">{value}</div>
        {sub && <div className="truncate text-[11px] text-slate-400">{sub}</div>}
      </div>
    </div>
  );
}
