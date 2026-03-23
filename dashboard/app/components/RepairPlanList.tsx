import type { RepairAction } from "../lib/mock-data";

const ACTION_COLORS: Record<string, string> = {
  REFETCH: "text-blue-400",
  VERIFY_WITH_SOURCE: "text-yellow-400",
  REBUILD_WORKING_SET: "text-orange-400",
};

export function RepairPlanList({ plan }: { plan: RepairAction[] }) {
  if (plan.length === 0) {
    return <p className="text-sm text-muted">No repairs needed.</p>;
  }

  return (
    <div className="space-y-3">
      {plan.map((action, i) => (
        <div key={i} className="border border-surface-light bg-surface rounded-lg p-4">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono bg-surface-light px-2 py-0.5 rounded">P{action.priority}</span>
            <span className={`font-mono text-sm font-semibold ${ACTION_COLORS[action.action] ?? "text-foreground"}`}>
              {action.action}
            </span>
            <span className="text-xs text-muted font-mono">{action.entry_id}</span>
          </div>
          <p className="text-sm text-muted">{action.reason}</p>
          <p className="text-xs text-gold mt-1 font-mono">
            Projected improvement: -{action.projected_improvement} points
          </p>
        </div>
      ))}
    </div>
  );
}
