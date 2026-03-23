"use client";

import Link from "next/link";
import { SettingsPanel } from "./SettingsPanel";

export function NavBar() {
  function handleSettingsSave() {
    // Trigger page reload to pick up new settings
    window.location.reload();
  }

  return (
    <nav className="border-b border-surface-light px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <Link href="/" className="font-mono text-gold text-lg font-bold">Sgraal</Link>
        <div className="flex items-center gap-5 text-sm text-muted">
          <a href="https://sgraal.com" className="hover:text-foreground transition">&larr; sgraal.com</a>
          <Link href="/" className="hover:text-foreground transition">Dashboard</Link>
          <Link href="/verify" className="hover:text-foreground transition">Verify</Link>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-xs text-muted font-mono">app.sgraal.com</span>
        <SettingsPanel onSave={handleSettingsSave} />
      </div>
    </nav>
  );
}
