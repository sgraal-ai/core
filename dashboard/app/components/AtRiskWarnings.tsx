import type { AtRiskWarning } from "../lib/mock-data";

export function AtRiskWarnings({ warnings }: { warnings: AtRiskWarning[] }) {
  if (warnings.length === 0) {
    return <p className="text-sm text-muted">No at-risk entries.</p>;
  }

  return (
    <div className="space-y-3">
      {warnings.map((w, i) => (
        <div key={i} className="border border-red-400/20 bg-red-400/5 rounded-lg p-4">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono text-red-400">{w.entry_id}</span>
            <span className="text-xs font-mono bg-red-400/10 text-red-400 px-2 py-0.5 rounded">
              importance: {w.importance_score}
            </span>
          </div>
          <p className="text-sm text-foreground/80">{w.warning}</p>
        </div>
      ))}
    </div>
  );
}
