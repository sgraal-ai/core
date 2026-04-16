"use client";

import { useState, useEffect, useCallback } from "react";
import { getApiKey, getApiUrl } from "../../lib/storage";
import { LoadingSkeleton, ConnectKeyState } from "../../components/LoadingSkeleton";

const DOMAINS = ["general", "customer_support", "coding", "legal", "fintech", "medical"];
const DEFAULTS = { warn: 25, ask_user: 45, block: 70 };
const CARD: React.CSSProperties = {
  background: "#ffffff",
  borderRadius: "8px",
  padding: "20px",
  boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
};

interface Thresholds {
  warn: number;
  ask_user: number;
  block: number;
}

interface DomainState {
  thresholds: Thresholds;
  source: string;
  dirty: boolean;
  saving: boolean;
  lastMessage: string | null;
}

function decisionAt(omega: number, t: Thresholds): string {
  if (omega < t.warn) return "USE_MEMORY";
  if (omega < t.ask_user) return "WARN";
  if (omega < t.block) return "ASK_USER";
  return "BLOCK";
}

function decisionColor(d: string): string {
  if (d === "USE_MEMORY") return "#16a34a";
  if (d === "WARN") return "#c9a962";
  if (d === "ASK_USER") return "#2563eb";
  return "#dc2626";
}

export default function CalibrationPage() {
  const [mounted, setMounted] = useState(false);
  const [hasKey, setHasKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [byDomain, setByDomain] = useState<Record<string, DomainState>>({});
  const [previewOmega, setPreviewOmega] = useState(65);
  const [previewDomain, setPreviewDomain] = useState("fintech");

  const load = useCallback(async () => {
    setMounted(true);
    const apiKey = getApiKey();
    setHasKey(!!apiKey);
    if (!apiKey) {
      setLoading(false);
      return;
    }
    const apiUrl = getApiUrl();
    const h = { Authorization: `Bearer ${apiKey}` };
    const next: Record<string, DomainState> = {};
    await Promise.all(
      DOMAINS.map(async (d) => {
        try {
          const r = await fetch(`${apiUrl}/v1/config/thresholds?domain=${d}`, { headers: h });
          if (r.ok) {
            const j = await r.json();
            next[d] = {
              thresholds: {
                warn: Number(j.thresholds?.warn ?? DEFAULTS.warn),
                ask_user: Number(j.thresholds?.ask_user ?? DEFAULTS.ask_user),
                block: Number(j.thresholds?.block ?? DEFAULTS.block),
              },
              source: String(j.source ?? "default"),
              dirty: false,
              saving: false,
              lastMessage: null,
            };
          } else {
            next[d] = {
              thresholds: { ...DEFAULTS },
              source: "default",
              dirty: false,
              saving: false,
              lastMessage: null,
            };
          }
        } catch {
          next[d] = {
            thresholds: { ...DEFAULTS },
            source: "default",
            dirty: false,
            saving: false,
            lastMessage: `Failed to load ${d}`,
          };
        }
      }),
    );
    setByDomain(next);
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const update = (domain: string, key: keyof Thresholds, value: number) => {
    setByDomain((prev) => {
      const cur = prev[domain] || {
        thresholds: { ...DEFAULTS },
        source: "default",
        dirty: false,
        saving: false,
        lastMessage: null,
      };
      const next = { ...cur.thresholds, [key]: value };
      return {
        ...prev,
        [domain]: { ...cur, thresholds: next, dirty: true, lastMessage: null },
      };
    });
  };

  const save = async (domain: string) => {
    const apiKey = getApiKey();
    if (!apiKey) return;
    const apiUrl = getApiUrl();
    const cur = byDomain[domain];
    if (!cur) return;
    setByDomain((prev) => ({
      ...prev,
      [domain]: { ...prev[domain], saving: true, lastMessage: null },
    }));
    try {
      const r = await fetch(`${apiUrl}/v1/config/thresholds`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          domain,
          warn: cur.thresholds.warn,
          ask_user: cur.thresholds.ask_user,
          block: cur.thresholds.block,
        }),
      });
      if (r.ok) {
        setByDomain((prev) => ({
          ...prev,
          [domain]: {
            ...prev[domain],
            saving: false,
            dirty: false,
            source: "custom",
            lastMessage: "Saved",
          },
        }));
      } else {
        const err = await r.json().catch(() => ({}));
        setByDomain((prev) => ({
          ...prev,
          [domain]: {
            ...prev[domain],
            saving: false,
            lastMessage: `Error: ${err.detail ?? r.statusText}`,
          },
        }));
      }
    } catch (e) {
      setByDomain((prev) => ({
        ...prev,
        [domain]: {
          ...prev[domain],
          saving: false,
          lastMessage: `Error: ${String(e)}`,
        },
      }));
    }
  };

  const reset = (domain: string) => {
    setByDomain((prev) => ({
      ...prev,
      [domain]: {
        ...prev[domain],
        thresholds: { ...DEFAULTS },
        dirty: true,
        lastMessage: null,
      },
    }));
  };

  if (!mounted) return null;
  if (!hasKey)
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Calibration</h1>
        <p className="text-muted text-sm mb-6">
          Tune decision thresholds per domain. Changes persist server-side.
        </p>
        <ConnectKeyState />
      </div>
    );
  if (loading)
    return (
      <div>
        <h1 className="text-2xl font-bold mb-1">Calibration</h1>
        <LoadingSkeleton rows={6} />
      </div>
    );

  const previewState = byDomain[previewDomain];
  const previewDecision = previewState
    ? decisionAt(previewOmega, previewState.thresholds)
    : "USE_MEMORY";

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-1">Calibration</h1>
          <p className="text-muted text-sm">
            Tune decision thresholds per domain. Changes persist server-side and apply to all
            future preflight calls.
          </p>
        </div>
      </div>

      {/* Live preview */}
      <div style={{ ...CARD, marginBottom: "24px" }}>
        <h2 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>Live preview</h2>
        <div style={{ display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <label
              style={{ fontSize: "12px", color: "#6b7280", display: "block", marginBottom: "4px" }}
            >
              Domain
            </label>
            <select
              value={previewDomain}
              onChange={(e) => setPreviewDomain(e.target.value)}
              style={{
                padding: "6px 10px",
                border: "1px solid #d1d5db",
                borderRadius: "4px",
                fontSize: "14px",
              }}
            >
              {DOMAINS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1, minWidth: "240px" }}>
            <label
              style={{ fontSize: "12px", color: "#6b7280", display: "block", marginBottom: "4px" }}
            >
              Omega: {previewOmega}
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={previewOmega}
              onChange={(e) => setPreviewOmega(Number(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <p style={{ fontSize: "12px", color: "#6b7280", margin: 0 }}>At omega {previewOmega} in {previewDomain}:</p>
            <p
              style={{
                fontSize: "20px",
                fontWeight: 700,
                color: decisionColor(previewDecision),
                margin: "2px 0 0 0",
                fontFamily: "monospace",
              }}
            >
              {previewDecision}
            </p>
          </div>
        </div>
      </div>

      {/* Per-domain sliders */}
      {DOMAINS.map((domain) => {
        const s = byDomain[domain];
        if (!s) return null;
        return (
          <div key={domain} style={{ ...CARD, marginBottom: "16px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "12px",
              }}
            >
              <div>
                <h3 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>{domain}</h3>
                <p style={{ fontSize: "12px", color: "#6b7280", margin: "2px 0 0 0" }}>
                  Source: {s.source}
                  {s.dirty ? " • unsaved changes" : ""}
                </p>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={() => reset(domain)}
                  style={{
                    padding: "6px 12px",
                    background: "#f3f4f6",
                    border: "1px solid #d1d5db",
                    borderRadius: "4px",
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Reset
                </button>
                <button
                  onClick={() => save(domain)}
                  disabled={!s.dirty || s.saving}
                  style={{
                    padding: "6px 12px",
                    background: s.dirty ? "#0B0F14" : "#9ca3af",
                    color: "#fff",
                    border: "none",
                    borderRadius: "4px",
                    fontSize: "13px",
                    cursor: s.dirty ? "pointer" : "not-allowed",
                  }}
                >
                  {s.saving ? "Saving..." : "Save"}
                </button>
              </div>
            </div>

            {(["warn", "ask_user", "block"] as const).map((key) => {
              const color =
                key === "warn" ? "#c9a962" : key === "ask_user" ? "#2563eb" : "#dc2626";
              return (
                <div key={key} style={{ marginBottom: "10px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "4px",
                    }}
                  >
                    <span style={{ fontSize: "13px", color: "#0B0F14", fontFamily: "monospace" }}>
                      {key.toUpperCase()}
                    </span>
                    <span style={{ fontSize: "13px", fontWeight: 700, color }}>
                      {s.thresholds[key]}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={100}
                    value={s.thresholds[key]}
                    onChange={(e) => update(domain, key, Number(e.target.value))}
                    style={{ width: "100%", accentColor: color }}
                  />
                </div>
              );
            })}

            {s.lastMessage && (
              <p
                style={{
                  fontSize: "12px",
                  color: s.lastMessage.startsWith("Error") ? "#dc2626" : "#16a34a",
                  marginTop: "8px",
                }}
              >
                {s.lastMessage}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
