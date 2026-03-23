"use client";

import { useState, useEffect } from "react";

interface SettingsPanelProps {
  onSave: (apiKey: string, apiUrl: string) => void;
}

export function SettingsPanel({ onSave }: SettingsPanelProps) {
  const [open, setOpen] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [apiUrl, setApiUrl] = useState("https://api.sgraal.com");

  useEffect(() => {
    setApiKey(localStorage.getItem("sgraal_api_key") ?? "");
    setApiUrl(localStorage.getItem("sgraal_api_url") ?? "https://api.sgraal.com");
  }, []);

  function handleSave() {
    localStorage.setItem("sgraal_api_key", apiKey);
    localStorage.setItem("sgraal_api_url", apiUrl);
    onSave(apiKey, apiUrl);
    setOpen(false);
  }

  function handleClear() {
    localStorage.removeItem("sgraal_api_key");
    localStorage.removeItem("sgraal_api_url");
    setApiKey("");
    setApiUrl("https://api.sgraal.com");
    onSave("", "https://api.sgraal.com");
    setOpen(false);
  }

  return (
    <>
      <button
        onClick={() => setOpen(!open)}
        className="text-muted hover:text-foreground transition"
        title="Settings"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="10" cy="10" r="3" />
          <path d="M10 1v2m0 14v2m-7-9H1m18 0h-2m-1.3-5.3l-1.4 1.4m-8.6 8.6l-1.4 1.4m0-11.4l1.4 1.4m8.6 8.6l1.4 1.4" />
        </svg>
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-end p-4" onClick={() => setOpen(false)}>
          <div
            className="bg-surface border border-surface-light rounded-xl p-6 w-96 mt-14 mr-2 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold mb-4">Settings</h3>

            <label className="block text-sm text-muted mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sg_live_..."
              className="w-full bg-background border border-surface-light rounded-lg px-4 py-2 text-sm font-mono text-foreground placeholder:text-muted focus:outline-none focus:border-gold transition mb-4"
            />

            <label className="block text-sm text-muted mb-1">API URL</label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full bg-background border border-surface-light rounded-lg px-4 py-2 text-sm font-mono text-foreground focus:outline-none focus:border-gold transition mb-6"
            />

            <div className="flex gap-3">
              <button
                onClick={handleSave}
                className="flex-1 bg-gold text-background font-semibold px-4 py-2 rounded-lg hover:bg-gold-dim transition text-sm"
              >
                Save & Connect
              </button>
              <button
                onClick={handleClear}
                className="px-4 py-2 rounded-lg border border-surface-light text-muted hover:text-foreground transition text-sm"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
