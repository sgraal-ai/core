"use client";
export default function GraphPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Memory Graph</h1>
      <p className="text-muted text-sm mb-6">Interactive force-directed graph of memory dependencies and risk.</p>
      <div className="bg-surface border border-surface-light rounded-xl p-10 text-center text-muted">
        <p className="text-sm">Connect API key in Settings to visualize your memory graph.</p>
        <p className="text-xs mt-2">Nodes = memory entries, edges = dependencies, color = omega risk score.</p>
      </div>
    </div>
  );
}
