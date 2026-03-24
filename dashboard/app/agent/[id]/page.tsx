"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import type { Agent } from "../../lib/mock-data";
import { getAgent } from "../../lib/mock-data";
import { DEMO_FLEET } from "../../lib/demo-fleet";
import { fetchPreflight } from "../../lib/api-client";
import { OmegaMeter } from "../../components/OmegaMeter";
import { ComponentBreakdown } from "../../components/ComponentBreakdown";
import { RepairPlanList } from "../../components/RepairPlanList";
import { AtRiskWarnings } from "../../components/AtRiskWarnings";
import { AdvancedAnalytics } from "../../components/AdvancedAnalytics";

const ACTION_STYLES: Record<string, { bg: string; text: string }> = {
  USE_MEMORY: { bg: "bg-green-400/10", text: "text-green-400" },
  WARN:       { bg: "bg-yellow-400/10", text: "text-yellow-400" },
  ASK_USER:   { bg: "bg-orange-400/10", text: "text-orange-400" },
  BLOCK:      { bg: "bg-red-400/10", text: "text-red-400" },
};

export default function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [agent, setAgent] = useState<Agent | null>(getAgent(id) ?? null);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    const apiKey = localStorage.getItem("sgraal_api_key") ?? "";
    const apiUrl = localStorage.getItem("sgraal_api_url") ?? "https://api.sgraal.com";

    if (!apiKey) return;

    const demo = DEMO_FLEET.find((d) => d.id === id);
    if (!demo) return;

    fetchPreflight(demo, apiKey, apiUrl)
      .then((liveAgent) => {
        setAgent(liveAgent);
        setIsLive(true);
      })
      .catch(() => {});
  }, [id]);

  if (!agent) {
    return (
      <div>
        <Link href="/" className="text-sm text-muted hover:text-foreground transition mb-6 inline-block">
          &larr; Back to fleet
        </Link>
        <p className="text-muted">Agent not found.</p>
      </div>
    );
  }

  const style = ACTION_STYLES[agent.recommended_action] ?? ACTION_STYLES.WARN;

  return (
    <div>
      <Link href="/" className="text-sm text-muted hover:text-foreground transition mb-6 inline-block">
        &larr; Back to fleet
      </Link>

      {isLive && (
        <div className="bg-green-400/10 border border-green-400/30 rounded-lg px-4 py-3 mb-6 text-sm text-green-400 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
          Live data from Sgraal API
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-8 mb-10">
        <OmegaMeter value={agent.omega_mem_final} size={140} />
        <div>
          <h1 className="text-2xl font-bold mb-1">{agent.name}</h1>
          <p className="text-xs text-muted font-mono mb-3">{agent.id}</p>
          <div className="flex flex-wrap gap-3 mb-4">
            <span className={`text-sm font-mono px-3 py-1 rounded ${style.bg} ${style.text}`}>
              {agent.recommended_action}
            </span>
            <span className="text-sm font-mono px-3 py-1 rounded bg-surface-light text-muted">
              {agent.domain}
            </span>
            <span className="text-sm font-mono px-3 py-1 rounded bg-surface-light text-muted">
              GSV: {agent.gsv}
            </span>
            <span className="text-sm font-mono px-3 py-1 rounded bg-surface-light text-muted">
              Healed: {agent.healing_counter}x
            </span>
          </div>
          <div className="flex gap-6 text-sm text-muted">
            <span>Assurance: <strong className="text-foreground">{agent.assurance_score}%</strong></span>
            <span>Profile: <strong className="text-foreground">{agent.compliance_result.profile_applied}</strong></span>
            {agent.compliance_result.audit_required && (
              <span className="text-red-400 font-mono">AUDIT REQUIRED</span>
            )}
          </div>
        </div>
      </div>

      {agent.compliance_result.violations.length > 0 && (
        <div className="border border-red-400/20 bg-red-400/5 rounded-xl p-5 mb-8">
          <h2 className="text-sm font-semibold text-red-400 mb-3">Compliance Violations</h2>
          {agent.compliance_result.violations.map((v, i) => (
            <div key={i} className="mb-2">
              <span className="text-xs font-mono text-red-400 mr-2">[{v.severity.toUpperCase()}]</span>
              <span className="text-xs font-mono text-gold mr-2">{v.article}</span>
              <span className="text-sm text-foreground/80">{v.description}</span>
            </div>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-8 mb-10">
        <div>
          <h2 className="text-lg font-semibold mb-4">Component Breakdown</h2>
          <div className="bg-surface border border-surface-light rounded-xl p-5">
            <ComponentBreakdown breakdown={agent.component_breakdown} />
          </div>
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-4">
            Repair Plan
            {agent.repair_plan.length > 0 && (
              <span className="text-sm text-gold ml-2">({agent.repair_plan.length})</span>
            )}
          </h2>
          <RepairPlanList plan={agent.repair_plan} />
        </div>
      </div>

      <div className="mb-10">
        <h2 className="text-lg font-semibold mb-4">
          At-Risk Warnings
          {agent.at_risk_warnings.length > 0 && (
            <span className="text-sm text-red-400 ml-2">({agent.at_risk_warnings.length})</span>
          )}
        </h2>
        <AtRiskWarnings warnings={agent.at_risk_warnings} />
      </div>

      <div className="mb-10">
        <h2 className="text-lg font-semibold mb-4">Advanced Analytics</h2>
        <AdvancedAnalytics
          calibration={agent.calibration}
          hawkes={agent.hawkes_intensity}
          copula={agent.copula_analysis}
          mewma={agent.mewma}
        />
      </div>
    </div>
  );
}
