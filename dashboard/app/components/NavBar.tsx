"use client";

import Link from "next/link";
import { SettingsPanel } from "./SettingsPanel";

export function NavBar() {
  function handleSettingsSave() {
    window.location.reload();
  }

  return (
    <nav className="border-b border-surface-light px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <a href="https://sgraal.com" className="font-mono text-gold text-lg font-bold">Sgraal</a>
        <div className="flex items-center gap-5 text-sm text-muted">
          <Link href="/verify" className="hover:text-foreground transition">Verify</Link>
        </div>
      </div>
      <SettingsPanel onSave={handleSettingsSave} />
    </nav>
  );
}
