"use client";

import { useState, useEffect, useRef } from "react";

const OMEGA_COLORS: Record<string, string> = {
  green: "#22c55e",
  yellow: "#eab308",
  orange: "#f97316",
  red: "#ef4444",
};

function getColor(omega: number) {
  if (omega < 25) return OMEGA_COLORS.green;
  if (omega < 50) return OMEGA_COLORS.yellow;
  if (omega < 75) return OMEGA_COLORS.orange;
  return OMEGA_COLORS.red;
}

interface MemNode {
  id: string;
  omega: number;
  type: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  contribution: number;
}

export default function ConsciousnessPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [nodes, setNodes] = useState<MemNode[]>([]);
  const [selected, setSelected] = useState<MemNode | null>(null);
  const [showingTop500, setShowingTop500] = useState(false);

  useEffect(() => {
    // Generate demo nodes (would come from API in production)
    const demo: MemNode[] = Array.from({ length: 50 }, (_, i) => ({
      id: `mem_${String(i).padStart(3, "0")}`,
      omega: Math.random() * 100,
      type: ["semantic", "preference", "tool_state", "episodic", "policy"][i % 5],
      x: 200 + Math.random() * 400,
      y: 150 + Math.random() * 300,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      contribution: Math.random() * 10,
    }));
    setNodes(demo);
    if (demo.length > 500) setShowingTop500(true);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const draw = () => {
      ctx.fillStyle = "#0B0F14";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      // Draw edges
      ctx.strokeStyle = "rgba(201, 169, 98, 0.1)";
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < Math.min(nodes.length, i + 3); j++) {
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
      // Draw nodes
      for (const n of nodes) {
        const r = 4 + n.contribution;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = getColor(n.omega);
        ctx.fill();
        // Simple physics
        n.x += n.vx;
        n.y += n.vy;
        n.vx *= 0.99;
        n.vy *= 0.99;
        // Bounce
        if (n.x < r || n.x > canvas.width - r) n.vx *= -1;
        if (n.y < r || n.y > canvas.height - r) n.vy *= -1;
      }
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => cancelAnimationFrame(animId);
  }, [nodes]);

  function handleCanvasClick(e: React.MouseEvent<HTMLCanvasElement>) {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const hit = nodes.find((n) => Math.hypot(n.x - x, n.y - y) < 10 + n.contribution);
    setSelected(hit || null);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Memory Consciousness</h1>
        <div className="flex gap-2">
          <button className="text-xs border border-surface-light px-3 py-1 rounded hover:bg-surface transition" data-testid="snapshot-btn"
            onClick={() => fetch("/v1/memory/snapshot", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ agent_id: "consciousness" }) }).catch(() => {})}>
            Snapshot
          </button>
          <button className="text-xs border border-surface-light px-3 py-1 rounded hover:bg-surface transition">Scan</button>
          <button className="text-xs border border-surface-light px-3 py-1 rounded hover:bg-surface transition">Red Team</button>
        </div>
      </div>

      {showingTop500 && (
        <div className="bg-yellow-900/30 border border-yellow-500/30 rounded p-2 text-xs text-yellow-300 mb-4" data-testid="top500-banner">
          Showing top 500 entries by contribution. Full graph available via API.
        </div>
      )}

      <div className="flex gap-2 mb-4 text-xs">
        {[
          { label: "< 25", color: OMEGA_COLORS.green },
          { label: "25-50", color: OMEGA_COLORS.yellow },
          { label: "50-75", color: OMEGA_COLORS.orange },
          { label: "75+", color: OMEGA_COLORS.red },
        ].map((l) => (
          <span key={l.label} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: l.color }} />
            {l.label}
          </span>
        ))}
      </div>

      <canvas ref={canvasRef} width={800} height={500}
        className="border border-surface-light rounded-lg w-full cursor-crosshair"
        onClick={handleCanvasClick} data-testid="consciousness-canvas" />

      {selected && (
        <div className="mt-4 border border-gold/30 bg-surface rounded-lg p-4">
          <p className="font-mono text-gold text-sm mb-1">{selected.id}</p>
          <p className="text-sm text-muted">Type: {selected.type} | Omega: {selected.omega.toFixed(1)} | Contribution: {selected.contribution.toFixed(1)}</p>
          <div className="flex gap-2 mt-2">
            <button className="text-xs bg-red-900 text-red-300 px-2 py-1 rounded">Quarantine</button>
            <button className="text-xs bg-gold/20 text-gold px-2 py-1 rounded">Heal</button>
          </div>
        </div>
      )}
    </div>
  );
}
