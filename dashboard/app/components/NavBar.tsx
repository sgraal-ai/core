"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { SettingsPanel } from "./SettingsPanel";

export function NavBar() {
  const [apiKey, setApiKey] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setApiKey(localStorage.getItem("sgraal_api_key") ?? "");
  }, []);

  function handleSettingsSave() {
    window.location.reload();
  }

  function truncateKey(key: string): string {
    if (key.length <= 16) return key;
    return key.slice(0, 12) + "..." + key.slice(-4);
  }

  function handleCopy() {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <nav className="border-b border-surface-light px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <a href="https://sgraal.com" className="font-mono text-gold text-lg font-bold">Sgraal</a>
        <div className="flex items-center gap-5 text-sm text-muted">
          <Link href="/verify" className="hover:text-foreground transition">Verify</Link>
        </div>
      </div>
      <div className="flex items-center gap-4">
        {apiKey ? (
          <div className="flex items-center gap-2">
            <span
              className="font-mono text-xs px-3 py-1.5 rounded-md"
              style={{
                background: "rgba(201,169,98,0.1)",
                border: "1px solid rgba(201,169,98,0.3)",
                color: "#c9a962",
              }}
            >
              {truncateKey(apiKey)}
            </span>
            <button
              onClick={handleCopy}
              className="text-xs text-muted hover:text-foreground transition"
              title="Copy API key"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        ) : (
          <Link
            href="/settings"
            className="text-sm font-semibold px-4 py-2 rounded-md transition-all"
            style={{ background: "#c9a962", color: "#0B0F14" }}
          >
            Get API Key &rarr;
          </Link>
        )}
        <SettingsPanel onSave={handleSettingsSave} />
      </div>
    </nav>
  );
}
