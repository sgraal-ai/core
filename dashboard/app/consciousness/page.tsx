"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Script from "next/script";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

interface MemNode {
  id: string;
  omega: number;
  type: string;
  contribution: number;
}

interface MemEdge {
  source: string;
  target: string;
}

interface D3Node extends MemNode {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

function nodeColor(omega: number): string {
  if (omega < 25) return "#16a34a";
  if (omega < 50) return "#c9a962";
  if (omega < 75) return "#f97316";
  return "#dc2626";
}

const CARD: React.CSSProperties = { background: "#ffffff", borderRadius: "8px", padding: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.06)" };
const BTN: React.CSSProperties = { padding: "6px 14px", borderRadius: "6px", border: "1px solid #e5e7eb", fontSize: "13px", cursor: "pointer", background: "#ffffff" };
const ZOOM_BTN: React.CSSProperties = { width: "32px", height: "32px", borderRadius: "6px", border: "1px solid #e5e7eb", background: "#ffffff", fontSize: "16px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" };

export default function ConsciousnessPage() {
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<{ zoomIn: () => void; zoomOut: () => void; reset: () => void } | null>(null);
  const [mounted, setMounted] = useState(false);
  const [d3Ready, setD3Ready] = useState(false);
  const [nodes, setNodes] = useState<MemNode[]>([]);
  const [edges, setEdges] = useState<MemEdge[]>([]);
  const [selected, setSelected] = useState<MemNode | null>(null);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showPanel, setShowPanel] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  function showToast(message: string, type: "success" | "error") {
    setToast({ message, type });
  }

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(t);
  }, [toast]);

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) {
      setLoading(false);
      return;
    }
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/memory/graph`, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (res.ok) {
        const d = await res.json();
        const rawNodes = d.nodes ?? [];
        const rawEdges = d.edges ?? [];
        if (rawNodes.length > 0) {
          setNodes(rawNodes.slice(0, 500).map((n: Record<string, unknown>, i: number) => ({
            id: String(n.id || `node_${i}`),
            omega: Number(n.omega ?? n.omega_mem_final ?? n.score ?? 0),
            type: String(n.type || n.memory_type || "unknown"),
            contribution: Number(n.contribution ?? n.shapley ?? n.weight ?? 5),
          })));
          setEdges(rawEdges.slice(0, 1000).map((e: Record<string, unknown>) => ({
            source: String(e.source ?? e.from ?? ""),
            target: String(e.target ?? e.to ?? ""),
          })).filter((e: MemEdge) => e.source && e.target));
        }
      }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  // D3 force simulation with zoom
  useEffect(() => {
    if (!d3Ready || !svgRef.current || nodes.length === 0) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const d3 = (window as any).d3 as any;
    if (!d3) return;

    const svg = d3.select(svgRef.current);
    const width = svgRef.current.clientWidth || 800;
    const height = 500;

    svg.selectAll("*").remove();

    // Container group for zoom/pan
    const g = svg.append("g");

    // Zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event: { transform: unknown }) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Expose zoom controls
    zoomRef.current = {
      zoomIn: () => svg.transition().duration(300).call(zoom.scaleBy, 1.5),
      zoomOut: () => svg.transition().duration(300).call(zoom.scaleBy, 0.67),
      reset: () => svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity),
    };

    const d3Nodes: D3Node[] = nodes.map((n) => ({ ...n }));
    const d3Edges = edges.map((e) => ({ source: e.source, target: e.target }));

    const simulation = d3.forceSimulation(d3Nodes as unknown[])
      .force("charge", d3.forceManyBody().strength(-400))
      .force("link", d3.forceLink(d3Edges).id((d: unknown) => (d as D3Node).id).distance(120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));

    const link = g.append("g").selectAll("line").data(d3Edges).join("line")
      .attr("stroke", "rgba(201,169,98,0.15)").attr("stroke-width", 1);

    const node = g.append("g").selectAll("circle").data(d3Nodes).join("circle")
      .attr("r", (d: D3Node) => 4 + d.contribution)
      .attr("fill", (d: D3Node) => nodeColor(d.omega))
      .attr("stroke", "#ffffff").attr("stroke-width", 1.5)
      .style("cursor", "pointer");

    const label = g.append("g").selectAll("text").data(d3Nodes).join("text")
      .text((d: D3Node) => d.id.slice(0, 10))
      .attr("font-size", "9px").attr("fill", "#6b7280").attr("text-anchor", "middle").attr("dy", (d: D3Node) => -(d.contribution + 8));

    // Tooltip
    d3.select(".sgraal-tooltip").remove();
    const tooltip = d3.select("body").append("div")
      .attr("class", "sgraal-tooltip")
      .style("position", "absolute").style("background", "#ffffff").style("border", "1px solid #e5e7eb")
      .style("border-radius", "6px").style("padding", "8px 12px").style("font-size", "12px")
      .style("pointer-events", "none").style("opacity", "0").style("box-shadow", "0 4px 12px rgba(0,0,0,0.1)")
      .style("z-index", "100").style("font-family", "monospace");

    node.on("mouseover", (event: MouseEvent, d: D3Node) => {
      tooltip.style("opacity", "1").html(`<b>${d.id}</b><br/>Omega: ${d.omega}<br/>Type: ${d.type}`);
    }).on("mousemove", (event: MouseEvent) => {
      tooltip.style("left", `${event.pageX + 12}px`).style("top", `${event.pageY - 20}px`);
    }).on("mouseout", () => {
      tooltip.style("opacity", "0");
    }).on("click", (_: MouseEvent, d: D3Node) => {
      setSelected(d);
      setShowPanel(true);
    });

    // Drag
    node.call(d3.drag()
      .on("start", (event: { active: number }, d: D3Node) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag", (event: { x: number; y: number }, d: D3Node) => { d.fx = event.x; d.fy = event.y; })
      .on("end", (event: { active: number }, d: D3Node) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
    );

    simulation.on("tick", () => {
      link.attr("x1", (d: { source: D3Node }) => d.source.x ?? 0).attr("y1", (d: { source: D3Node }) => d.source.y ?? 0)
        .attr("x2", (d: { target: D3Node }) => d.target.x ?? 0).attr("y2", (d: { target: D3Node }) => d.target.y ?? 0);
      node.attr("cx", (d: D3Node) => d.x ?? 0).attr("cy", (d: D3Node) => d.y ?? 0);
      label.attr("x", (d: D3Node) => d.x ?? 0).attr("y", (d: D3Node) => d.y ?? 0);
    });

    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [d3Ready, nodes, edges]);

  async function handleScan() {
    const apiKey = getApiKey();
    if (!apiKey) return;
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/memory/scan`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: "consciousness", scan_depth: "quick" }),
      });
      if (res.ok) {
        const data = await res.json();
        const count = data.sleepers_found ?? data.count ?? 0;
        showToast(`Scan complete — ${count} sleepers found`, "success");
      } else {
        showToast("Scan failed", "error");
      }
    } catch {
      showToast("Scan failed", "error");
    }
  }

  async function handleSnapshot() {
    const apiKey = getApiKey();
    if (!apiKey) return;
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/memory/snapshot`, {
        method: "POST",
        headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: "consciousness", label: "manual snapshot" }),
      });
      if (res.ok) {
        showToast("Snapshot created \u2713", "success");
      } else {
        showToast("Snapshot failed", "error");
      }
    } catch {
      showToast("Snapshot failed", "error");
    }
  }

  async function handleHeal(entryId: string) {
    const apiKey = getApiKey();
    if (!apiKey) return;
    const apiUrl = getApiUrl();
    try {
      const res = await fetch(`${apiUrl}/v1/heal`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ entry_id: entryId, action: "REFETCH" }),
      });
      if (res.ok) showToast(`Healed ${entryId}`, "success");
      else showToast("Heal failed", "error");
    } catch {
      showToast("Heal failed", "error");
    }
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Memory Graph</h1>
      <p className="text-muted text-sm mb-6">Force-directed visualization of memory entries and their relationships.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Memory Graph</h1>
      <p className="text-muted text-sm mb-6">Force-directed visualization of memory entries and their relationships.</p>
      <LoadingSkeleton rows={5} />
    </div>
  );

  if (nodes.length === 0) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Memory Graph</h1>
      <p className="text-muted text-sm mb-6">Force-directed visualization of memory entries and their relationships.</p>
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <p style={{ fontSize: "48px", color: "#c9a962" }}>&#x25CB;</p>
        <h3 style={{ fontSize: "20px", color: "#0B0F14", fontWeight: 700, marginTop: "8px" }}>No memory entries yet</h3>
        <p style={{ fontSize: "14px", color: "#6b7280", marginTop: "8px", maxWidth: "400px", margin: "8px auto 0" }}>
          Store memories via <code style={{ color: "#c9a962" }}>POST /v1/store/memories</code> to see them visualized here.
        </p>
      </div>
    </div>
  );

  return (
    <div style={{ position: "relative" }}>
      <Script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js" integrity="sha384-su5kReKyYlIFrI62mbQRKXHzFobMa7BHp1cK6julLPbnYcCW9NIZKJiTODjLPeDh" crossOrigin="anonymous" onLoad={() => setD3Ready(true)} />

      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">Memory Graph</h1>
          <p className="text-muted text-sm">Force-directed visualization of memory entries and their relationships.</p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button onClick={handleScan} style={BTN}>Scan for sleepers</button>
          <button onClick={handleSnapshot} style={BTN}>Take snapshot</button>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", gap: "16px", marginBottom: "12px", fontSize: "12px" }}>
        {[{ label: "< 25", color: "#16a34a" }, { label: "25-50", color: "#c9a962" }, { label: "50-75", color: "#f97316" }, { label: "> 75", color: "#dc2626" }].map((l) => (
          <span key={l.label} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: "10px", height: "10px", borderRadius: "50%", background: l.color, display: "inline-block" }} />
            <span style={{ color: "#6b7280" }}>Omega {l.label}</span>
          </span>
        ))}
        {nodes.length > 0 && <span style={{ color: "#6b7280", marginLeft: "auto" }}>Showing {nodes.length} entries</span>}
      </div>

      {/* Graph */}
      <div style={{ ...CARD, padding: "0", overflow: "hidden", position: "relative" }}>
        <svg ref={svgRef} width="100%" height="500" style={{ display: "block", background: "#faf9f6" }} />
        {/* Zoom controls */}
        <div style={{ position: "absolute", top: "12px", right: "12px", display: "flex", flexDirection: "column", gap: "4px" }}>
          <button style={ZOOM_BTN} onClick={() => zoomRef.current?.zoomIn()} title="Zoom in">+</button>
          <button style={ZOOM_BTN} onClick={() => zoomRef.current?.zoomOut()} title="Zoom out">−</button>
          <button style={ZOOM_BTN} onClick={() => zoomRef.current?.reset()} title="Reset zoom">⊡</button>
        </div>
      </div>

      {/* Side Panel */}
      {showPanel && selected && (
        <div
          style={{
            position: "fixed", top: 0, right: 0, width: "360px", height: "100vh",
            background: "#ffffff", boxShadow: "-4px 0 24px rgba(0,0,0,0.1)",
            padding: "24px", overflowY: "auto", zIndex: 50,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
            <h3 style={{ fontSize: "16px", fontWeight: 700 }}>Entry Details</h3>
            <button onClick={() => setShowPanel(false)} style={{ fontSize: "20px", color: "#6b7280", cursor: "pointer", background: "none", border: "none" }}>×</button>
          </div>

          <p style={{ fontFamily: "monospace", fontSize: "14px", fontWeight: 600, marginBottom: "16px", color: "#0B0F14" }}>{selected.id}</p>

          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "4px" }}>Omega Score</p>
            <p style={{ fontSize: "36px", fontWeight: 700, color: nodeColor(selected.omega) }}>{selected.omega}</p>
          </div>

          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "4px" }}>Memory Type</p>
            <p style={{ fontSize: "14px", color: "#0B0F14" }}>{selected.type}</p>
          </div>

          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "4px" }}>Contribution</p>
            <p style={{ fontSize: "14px", color: "#0B0F14" }}>{selected.contribution.toFixed(1)}</p>
          </div>

          {/* Mock component breakdown */}
          <div style={{ marginBottom: "24px" }}>
            <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "8px" }}>Component Breakdown (estimated)</p>
            {(() => {
              const components = ["s_freshness", "s_drift", "s_provenance", "s_interference", "s_propagation", "r_recall", "r_encode", "r_belief", "s_relevance", "r_recovery"];
              const stableValues: Record<string, number> = {};
              for (const c of components) {
                const str = selected.id + c;
                let hash = 0;
                for (let i = 0; i < str.length; i++) {
                  hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
                }
                stableValues[c] = Math.round(((Math.abs(hash) % 1000) / 1000) * selected.omega + 10);
              }
              return components.map((c) => {
                const v = stableValues[c];
                return (
                  <div key={c} style={{ marginBottom: "6px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#6b7280", marginBottom: "2px" }}><span>{c}</span><span>{Math.min(v, 100)}</span></div>
                    <div style={{ height: "4px", background: "#e5e7eb", borderRadius: "2px", overflow: "hidden" }}>
                      <div style={{ width: `${Math.min(v, 100)}%`, height: "100%", background: v > 60 ? "#dc2626" : v > 30 ? "#c9a962" : "#16a34a", borderRadius: "2px" }} />
                    </div>
                  </div>
                );
              });
            })()}
          </div>

          {selected.omega > 30 && (
            <div style={{ marginBottom: "24px" }}>
              <p style={{ fontSize: "11px", color: "#6b7280", textTransform: "uppercase", marginBottom: "8px" }}>Repair Plan</p>
              <ul style={{ fontSize: "13px", color: "#0B0F14", paddingLeft: "16px" }}>
                <li>REFETCH stale data</li>
                {selected.omega > 50 && <li>VERIFY_WITH_SOURCE</li>}
                {selected.omega > 70 && <li>REBUILD_WORKING_SET</li>}
              </ul>
            </div>
          )}

          <button
            onClick={() => handleHeal(selected.id)}
            style={{ width: "100%", background: "#c9a962", color: "#0B0F14", fontWeight: 600, padding: "10px", borderRadius: "6px", fontSize: "14px", border: "none", cursor: "pointer" }}
          >
            Heal this entry
          </button>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          style={{
            position: "fixed", bottom: "24px", right: "24px",
            background: toast.type === "success" ? "#16a34a" : "#dc2626",
            color: "white", padding: "12px 24px", borderRadius: "8px",
            fontSize: "14px", fontWeight: 600,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)", zIndex: 100,
          }}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}
