export function ComponentBreakdown({ breakdown }: { breakdown: Record<string, number> }) {
  const maxVal = Math.max(...Object.values(breakdown), 1);

  return (
    <div className="space-y-2">
      {Object.entries(breakdown).map(([key, value]) => {
        const pct = (value / maxVal) * 100;
        const color =
          value < 25 ? "bg-green-400" : value < 50 ? "bg-yellow-400" : value < 75 ? "bg-orange-400" : "bg-red-400";

        return (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs font-mono text-muted w-28 text-right shrink-0">{key}</span>
            <div className="flex-1 bg-surface-light rounded-full h-3 overflow-hidden">
              <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
            </div>
            <span className="text-xs font-mono w-10 text-right">{value}</span>
          </div>
        );
      })}
    </div>
  );
}
