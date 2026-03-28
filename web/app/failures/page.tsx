export const metadata = {
  title: "Failure Gallery — Sgraal",
  description: "5 real-world AI agent memory failures and how Sgraal catches each one before they cause damage.",
};

const FAILURES = [
  {
    title: "Stale Preference",
    scenario: "A customer support agent recommends a product the user explicitly rejected 2 months ago. The preference memory is 60 days old and was never refreshed.",
    sgraalResponse: {
      component: "s_freshness",
      score: 89.2,
      action: "BLOCK",
      detail: "Memory is stale (freshness=89.2/100, type=preference). Weibull decay for preference type triggered at 60 days.",
    },
    repairAction: "REFETCH — retrieve current user preferences before acting",
    color: "text-red-400",
  },
  {
    title: "Conflicting Facts",
    scenario: "Two trusted sources disagree about a customer's account status. Source A says 'active', Source B says 'suspended'. The agent has no way to know which is current.",
    sgraalResponse: {
      component: "s_interference + sheaf cohomology",
      score: 67.4,
      action: "ASK_USER",
      detail: "Sheaf H1 rank = 1 (inconsistent cycle detected). 2 entries with source_trust > 0.8 contradict each other.",
    },
    repairAction: "VERIFY_WITH_SOURCE — resolve conflict before proceeding",
    color: "text-yellow-400",
  },
  {
    title: "Poisoned Source",
    scenario: "An API endpoint that the agent relies on starts returning manipulated data. Trust score for this source has been steadily dropping over 48 hours.",
    sgraalResponse: {
      component: "poisoning_suspected",
      score: 91.0,
      action: "BLOCK",
      detail: "Trust decay detected: source trust dropped from 0.92 to 0.31 over 48 hours. Forensics ID generated for investigation.",
    },
    repairAction: "BLOCK + forensics_id issued for security review",
    color: "text-red-400",
  },
  {
    title: "Goal Drift",
    scenario: "A coding assistant agent's memory was built for Python backend tasks, but the user has shifted to React frontend work. The agent keeps suggesting Flask patterns.",
    sgraalResponse: {
      component: "goal_drift",
      score: 0.71,
      action: "WARN",
      detail: "Agent goal drift detected (drift_score=0.71, threshold=0.3). Memory baseline misaligned with current task context.",
    },
    repairAction: "GOAL_DRIFT_WARNING — review memory alignment with current objective",
    color: "text-yellow-400",
  },
  {
    title: "Regulatory Gap",
    scenario: "A fintech agent is about to make an irreversible trade recommendation based on memory with omega > 60. EU AI Act Article 12 requires full traceability for high-risk decisions.",
    sgraalResponse: {
      component: "EU AI Act Article 12",
      score: 72.0,
      action: "BLOCK",
      detail: "Compliance violation: omega_mem_final > 60 AND action_type == 'irreversible'. Article 12 requires audit trail. Decision blocked until memory quality improves.",
    },
    repairAction: "BLOCK — cannot proceed without compliant memory state",
    color: "text-red-400",
  },
];

export default function FailuresPage() {
  return (
    <div className="max-w-4xl mx-auto py-16 px-6">
      <p className="text-gold font-mono text-sm tracking-widest uppercase mb-4">Failure Gallery</p>
      <h1 className="text-3xl sm:text-4xl font-bold mb-4">5 failures Sgraal catches before they happen</h1>
      <p className="text-muted text-lg mb-12">
        Every failure below is a real pattern that causes production incidents in AI agents.
        Here is exactly how Sgraal detects and prevents each one.
      </p>

      <div className="space-y-8">
        {FAILURES.map((f, i) => (
          <div key={i} className="border border-surface-light rounded-xl overflow-hidden">
            <div className="bg-surface px-6 py-4 border-b border-surface-light flex items-center justify-between">
              <h3 className="font-semibold text-foreground">{i + 1}. {f.title}</h3>
              <span className={`font-mono text-sm font-bold ${f.color}`}>{f.sgraalResponse.action}</span>
            </div>
            <div className="p-6">
              <div className="mb-4">
                <p className="text-muted text-xs uppercase tracking-wider mb-1">Scenario</p>
                <p className="text-foreground/80 text-sm">{f.scenario}</p>
              </div>
              <div className="bg-background border border-surface-light rounded-lg p-4 mb-4 font-mono text-sm">
                <p className="text-muted mb-1">// Sgraal response</p>
                <p><span className="text-muted">component:</span> <span className="text-gold">{f.sgraalResponse.component}</span></p>
                <p><span className="text-muted">score:</span> <span className="text-foreground">{f.sgraalResponse.score}</span></p>
                <p><span className="text-muted">action:</span> <span className={f.color}>{f.sgraalResponse.action}</span></p>
                <p className="text-foreground/70 mt-2 text-xs">{f.sgraalResponse.detail}</p>
              </div>
              <div>
                <p className="text-muted text-xs uppercase tracking-wider mb-1">Repair action</p>
                <p className="text-foreground/90 text-sm font-mono">{f.repairAction}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="text-center mt-12">
        <a href="/playground" className="bg-gold text-background font-semibold px-8 py-3 rounded-lg hover:bg-gold-dim transition inline-block">
          Test your own memory state →
        </a>
      </div>
    </div>
  );
}
