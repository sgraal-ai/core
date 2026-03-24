import type { Calibration, HawkesIntensity, CopulaAnalysis, MEWMA } from "../lib/mock-data";

function Badge({ label, active, color }: { label: string; active: boolean; color: "green" | "red" | "yellow" }) {
  const colors = {
    green: active ? "bg-green-400/10 text-green-400" : "bg-surface-light text-muted",
    red: active ? "bg-red-400/10 text-red-400" : "bg-surface-light text-muted",
    yellow: active ? "bg-yellow-400/10 text-yellow-400" : "bg-surface-light text-muted",
  };
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded ${colors[color]}`}>
      {label}
    </span>
  );
}

function MetricCard({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="bg-surface border border-surface-light rounded-lg p-3">
      <p className="text-xs text-muted mb-1">{label}</p>
      <p className="text-lg font-bold font-mono">
        {value}
        {unit && <span className="text-xs text-muted ml-1">{unit}</span>}
      </p>
    </div>
  );
}

function GaugeBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-surface-light rounded-full h-3 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono w-16 text-right">{value} / {max}</span>
    </div>
  );
}

export function AdvancedAnalytics({
  calibration,
  hawkes,
  copula,
  mewma,
}: {
  calibration?: Calibration;
  hawkes?: HawkesIntensity;
  copula?: CopulaAnalysis;
  mewma?: MEWMA;
}) {
  if (!calibration && !hawkes && !copula && !mewma) {
    return <p className="text-sm text-muted">No advanced analytics available.</p>;
  }

  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Calibration */}
      {calibration && (
        <div className="border border-surface-light bg-surface rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gold mb-4">Calibration</h3>
          <div className="grid grid-cols-3 gap-3">
            <MetricCard label="Brier Score" value={calibration.brier_score} />
            <MetricCard label="Log Loss" value={calibration.log_loss} />
            <MetricCard label="Meta Score" value={calibration.meta_score} unit="/100" />
          </div>
        </div>
      )}

      {/* Hawkes */}
      {hawkes && (
        <div className="border border-surface-light bg-surface rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gold mb-4">Hawkes Intensity</h3>
          <div className="flex items-center gap-3 mb-3">
            <Badge label={hawkes.burst_detected ? "BURST" : "NORMAL"} active={hawkes.burst_detected} color="red" />
            <Badge label={hawkes.excited ? "EXCITED" : "CALM"} active={hawkes.excited} color="yellow" />
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-muted">λ current:</span>
            <span className="font-mono font-bold">{hawkes.current_lambda}</span>
            <span className="text-muted">μ baseline:</span>
            <span className="font-mono">{hawkes.baseline_mu}</span>
          </div>
        </div>
      )}

      {/* Copula */}
      {copula && (
        <div className="border border-surface-light bg-surface rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gold mb-4">Copula Joint Risk</h3>
          <div className="flex items-center gap-3 mb-3">
            <Badge
              label={copula.tail_dependence ? "TAIL DEPENDENCE" : "INDEPENDENT"}
              active={copula.tail_dependence}
              color="red"
            />
            <span className="text-xs text-muted font-mono">ρ = {copula.rho}</span>
          </div>
          <p className="text-xs text-muted mb-2">Joint Risk</p>
          <GaugeBar
            value={copula.joint_risk}
            max={100}
            color={copula.joint_risk > 50 ? "bg-red-400" : copula.joint_risk > 25 ? "bg-yellow-400" : "bg-green-400"}
          />
        </div>
      )}

      {/* MEWMA */}
      {mewma && (
        <div className="border border-surface-light bg-surface rounded-xl p-5">
          <h3 className="text-sm font-semibold text-gold mb-4">MEWMA Control</h3>
          <div className="flex items-center gap-3 mb-3">
            <Badge
              label={mewma.out_of_control ? "OUT OF CONTROL" : "IN CONTROL"}
              active={mewma.out_of_control}
              color="red"
            />
          </div>
          <p className="text-xs text-muted mb-2">Hotelling T² vs limit</p>
          <GaugeBar
            value={Math.round(mewma.T2_stat * 10) / 10}
            max={mewma.control_limit}
            color={mewma.out_of_control ? "bg-red-400" : mewma.T2_stat > mewma.control_limit * 0.7 ? "bg-yellow-400" : "bg-green-400"}
          />
          <p className="text-xs text-muted mt-2 font-mono">
            Monitoring: {mewma.monitored_components.join(", ")}
          </p>
        </div>
      )}
    </div>
  );
}
