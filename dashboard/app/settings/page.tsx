"use client";

import { useState, useEffect } from "react";
import { getApiKey, getApiUrl, setApiKey as saveApiKey, setApiUrl as saveApiUrl, removeApiKey, removeApiUrl, getItem, setItem, removeItem } from "../lib/storage";

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("");
  const [savedKey, setSavedKey] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const stored = getApiKey();
    if (stored) {
      setSavedKey(stored);
      setApiKey(stored);
    }
  }, []);

  function handleSave() {
    const trimmed = apiKey.trim();
    if (!trimmed) return;
    saveApiKey(trimmed);
    setSavedKey(trimmed);
  }

  function handleRemove() {
    removeApiKey();
    setApiKey("");
    setSavedKey("");
  }

  function handleCopy() {
    navigator.clipboard.writeText(savedKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function truncateKey(key: string): string {
    if (key.length <= 16) return key;
    return key.slice(0, 12) + "..." + key.slice(-4);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Settings</h1>
      <p className="text-muted text-sm mb-6">Manage your API key and dashboard preferences.</p>

      <div className="bg-surface border border-surface-light rounded-xl p-6 mb-6 max-w-lg">
        <h2 className="text-lg font-semibold mb-4">Your API Key</h2>

        {savedKey ? (
          <div>
            <div className="flex items-center gap-3 mb-3">
              <span className="font-mono text-sm bg-gold/10 border border-gold/30 text-gold px-3 py-2 rounded-lg">
                {truncateKey(savedKey)}
              </span>
              <button
                onClick={handleCopy}
                className="text-sm text-muted hover:text-foreground transition px-3 py-2 border border-surface-light rounded-lg"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
              <button
                onClick={handleRemove}
                className="text-sm text-red-400 hover:text-red-300 transition px-3 py-2 border border-red-400/30 rounded-lg"
              >
                Remove
              </button>
            </div>
            <p className="text-xs text-muted">Key is stored in your browser only (localStorage).</p>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-3 mb-3">
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sg_live_..."
                className="flex-1 bg-background border border-surface-light rounded-lg px-4 py-2 text-sm font-mono text-foreground placeholder:text-muted focus:outline-none focus:border-gold transition"
              />
              <button
                onClick={handleSave}
                className="bg-gold text-background font-semibold px-5 py-2 rounded-lg hover:bg-gold-dim transition text-sm"
              >
                Save
              </button>
            </div>
            <p className="text-sm text-muted">
              {"Don't have a key? "}
              <a href="https://sgraal.com" className="text-gold hover:underline transition">
                Get one free at sgraal.com &rarr;
              </a>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
