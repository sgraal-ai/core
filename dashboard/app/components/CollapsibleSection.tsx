"use client";
import { useState, type ReactNode } from "react";

export function CollapsibleSection({ title, children, badge }: { title: string; children: ReactNode; badge?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-surface-light rounded-xl mb-3 overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-5 py-3 text-sm font-semibold text-left hover:bg-surface-light/50 transition">
        <span>{title} {badge && <span className="text-xs text-gold font-mono ml-2">{badge}</span>}</span>
        <span className="text-muted text-xs">{open ? "collapse" : "expand"}</span>
      </button>
      {open && <div className="px-5 pb-4 border-t border-surface-light">{children}</div>}
    </div>
  );
}

export function KV({ label, value }: { label: string; value: unknown }) {
  if (value === undefined || value === null) return null;
  const display = typeof value === "boolean" ? (value ? "true" : "false") : typeof value === "object" ? JSON.stringify(value) : String(value);
  const color = typeof value === "boolean" ? (value ? "text-red-400" : "text-green-400") : "text-foreground";
  return (
    <div className="flex justify-between py-1 text-xs border-b border-surface-light/50 last:border-0">
      <span className="text-muted font-mono">{label}</span>
      <span className={`font-mono ${color}`}>{display}</span>
    </div>
  );
}
