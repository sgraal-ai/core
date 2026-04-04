"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../components/LoadingSkeleton";

const CARD = "bg-surface border border-surface-light rounded-xl p-5";

export default function ComplyPage() {
  const [mounted, setMounted] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);

  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [declaration, setDeclaration] = useState<Record<string, unknown> | null>(null);
  const [auditVerify, setAuditVerify] = useState<Record<string, unknown> | null>(null);
  const [gdpr, setGdpr] = useState<Record<string, unknown> | null>(null);
  const [showDeclarationJson, setShowDeclarationJson] = useState(false);

  function headers() {
    return { Authorization: `Bearer ${getApiKey()}`, "Content-Type": "application/json" };
  }

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) { setLoading(false); return; }
    const base = getApiUrl();
    const h = { Authorization: `Bearer ${apiKey}` };

    await Promise.all([
      fetch(`${base}/v1/compliance/eu-ai-act/report`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setReport(d)).catch(() => {}),
      fetch(`${base}/v1/audit-log/verify`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setAuditVerify(d)).catch(() => {}),
      fetch(`${base}/v1/compliance/gdpr`, { headers: h }).then(r => r.ok ? r.json() : null).then(d => d && setGdpr(d)).catch(() => {}),
    ]);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function refreshReport() {
    const base = getApiUrl();
    try {
      const res = await fetch(`${base}/v1/compliance/eu-ai-act/report`, { headers: headers() });
      if (res.ok) setReport(await res.json());
    } catch {}
  }

  async function fetchDeclaration() {
    const base = getApiUrl();
    try {
      const res = await fetch(`${base}/v1/compliance/eu-ai-act/declaration`, { headers: headers() });
      if (res.ok) { setDeclaration(await res.json()); setShowDeclarationJson(true); }
    } catch {}
  }

  if (!mounted) return null;

  if (!hasKey) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Comply</h1>
      <p className="text-muted text-sm mb-6">Regulatory compliance, audit integrity, and GDPR.</p>
      <ConnectKeyState />
    </div>
  );

  if (loading) return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Comply</h1>
      <p className="text-muted text-sm mb-6">Regulatory compliance, audit integrity, and GDPR.</p>
      <LoadingSkeleton rows={4} />
    </div>
  );

  const conformityScore = Number(report?.conformity_score ?? report?.score ?? 0);
  const scoreColor = conformityScore >= 90 ? "#16a34a" : conformityScore >= 70 ? "#c9a962" : "#dc2626";
  const articles = (report?.articles_addressed ?? report?.articles ?? []) as string[];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Comply</h1>
      <p className="text-muted text-sm mb-6">Regulatory compliance, audit integrity, and GDPR.</p>

      {/* EU AI Act Report */}
      <div className={`${CARD} mb-6`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">EU AI Act Report</h2>
          <button onClick={refreshReport} className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition">Refresh Report</button>
        </div>
        {report ? (
          <div>
            <div className="flex items-center gap-6 mb-4">
              <div>
                <p className="text-xs text-muted uppercase mb-1">Conformity Score</p>
                <p className="text-4xl font-bold" style={{ color: scoreColor }}>{conformityScore}</p>
              </div>
              <div className="flex-1">
                <p className="text-xs text-muted uppercase mb-1">Articles Addressed</p>
                <div className="flex flex-wrap gap-2">
                  {articles.map((a, i) => (
                    <span key={i} className="text-xs font-mono px-2 py-1 rounded bg-gold/10 text-gold">{String(a)}</span>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
              {report.article_13_transparency !== undefined && (
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Article 13 — Transparency</p>
                  <p className="font-semibold">{String((report.article_13_transparency as Record<string, unknown>)?.compliant ?? report.article_13_transparency)}</p>
                </div>
              )}
              {report.article_14_human_oversight !== undefined && (
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Article 14 — Human Oversight</p>
                  <p className="font-semibold">{String((report.article_14_human_oversight as Record<string, unknown>)?.compliant ?? report.article_14_human_oversight)}</p>
                </div>
              )}
              {report.article_17_quality_management !== undefined && (
                <div>
                  <p className="text-xs text-muted uppercase mb-1">Article 17 — Quality Management</p>
                  <p className="font-semibold">{String((report.article_17_quality_management as Record<string, unknown>)?.compliant ?? report.article_17_quality_management)}</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted">No report data available. Run preflight calls to generate compliance data.</p>
        )}
      </div>

      {/* EU AI Act Declaration */}
      <div className={`${CARD} mb-6`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">EU AI Act Declaration</h2>
          <button onClick={fetchDeclaration} className="text-sm font-semibold px-4 py-1.5 rounded bg-gold text-background hover:bg-gold-dim transition">Download Declaration</button>
        </div>
        {showDeclarationJson && declaration ? (
          <div>
            <div className="grid grid-cols-2 gap-4 text-sm mb-4">
              {!!declaration.title && <div><p className="text-xs text-muted uppercase mb-1">Title</p><p className="font-semibold">{String(declaration.title)}</p></div>}
              {!!declaration.date && <div><p className="text-xs text-muted uppercase mb-1">Date</p><p className="font-mono text-xs">{String(declaration.date)}</p></div>}
              {!!declaration.preflight_mechanism && <div><p className="text-xs text-muted uppercase mb-1">Preflight Mechanism</p><p>{String(declaration.preflight_mechanism)}</p></div>}
              {!!declaration.human_oversight && <div><p className="text-xs text-muted uppercase mb-1">Human Oversight</p><p>{String(declaration.human_oversight)}</p></div>}
              {!!declaration.transparency && <div><p className="text-xs text-muted uppercase mb-1">Transparency</p><p>{String(declaration.transparency)}</p></div>}
              {!!declaration.record_keeping && <div><p className="text-xs text-muted uppercase mb-1">Record Keeping</p><p>{String(declaration.record_keeping)}</p></div>}
            </div>
            <pre className="text-xs font-mono text-muted bg-surface-light rounded-lg p-4 overflow-x-auto max-h-48 overflow-y-auto">
              {JSON.stringify(declaration, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="text-sm text-muted">Click &quot;Download Declaration&quot; to generate an EU AI Act conformity declaration.</p>
        )}
      </div>

      {/* Audit Log Integrity */}
      <div className={`${CARD} mb-6`}>
        <h2 className="text-lg font-semibold mb-4">Audit Log Integrity</h2>
        {auditVerify ? (
          <div>
            <div className="flex items-center gap-4 mb-3">
              <span style={{ fontSize: "36px", color: auditVerify.valid ? "#16a34a" : "#dc2626" }}>
                {auditVerify.valid ? "\u2713" : "\u2717"}
              </span>
              <div>
                <p className="text-sm font-semibold">{auditVerify.valid ? "All audit records verified — no tampering detected." : `WARNING: ${auditVerify.tampered_count ?? 0} tampered records detected.`}</p>
                <p className="text-xs text-muted mt-1">Checked: {String(auditVerify.total_checked ?? 0)} records</p>
              </div>
            </div>
            {Number(auditVerify.tampered_count ?? 0) > 0 && (
              <p className="text-sm text-red-400">Tampered: {String(auditVerify.tampered_count)} records require investigation.</p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted">Audit verification unavailable. Ensure audit logging is enabled.</p>
        )}
      </div>

      {/* GDPR Policy */}
      <div className={CARD}>
        <h2 className="text-lg font-semibold mb-4">GDPR Policy</h2>
        {gdpr ? (
          <div className="space-y-4">
            {!!gdpr.data_location && (
              <div><p className="text-xs text-muted uppercase mb-1">Data Location</p><p className="text-sm">{String(gdpr.data_location)}</p></div>
            )}
            {!!gdpr.dpa_contact && (
              <div><p className="text-xs text-muted uppercase mb-1">DPA Contact</p><p className="text-sm font-mono">{String(gdpr.dpa_contact)}</p></div>
            )}
            {!!gdpr.right_to_erasure && (
              <div><p className="text-xs text-muted uppercase mb-1">Right to Erasure</p><p className="text-sm">{String(gdpr.right_to_erasure)}</p></div>
            )}
            {Array.isArray(gdpr.data_retention) && (
              <div>
                <p className="text-xs text-muted uppercase mb-2">Data Retention</p>
                <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {["Data Type", "Retention"].map(h => (
                        <th key={h} className="text-xs text-muted uppercase text-left pb-2 pr-4" style={{ borderBottom: "1px solid #e5e7eb" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(gdpr.data_retention as Array<Record<string, unknown>>).map((r, i) => (
                      <tr key={i}>
                        <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(r.type ?? r.data_type ?? r.name ?? "")}</td>
                        <td className="py-2 pr-4 text-sm" style={{ borderBottom: "1px solid #f5f4f0" }}>{String(r.retention ?? r.period ?? r.duration ?? "")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted">GDPR policy data unavailable.</p>
        )}
      </div>
    </div>
  );
}
