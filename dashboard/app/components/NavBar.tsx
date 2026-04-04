"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { getApiKey, getApiUrl, setApiKey as saveApiKey, setApiUrl as saveApiUrl, removeApiKey, removeApiUrl, getItem, setItem, removeItem } from "../lib/storage";

interface DropdownItem {
  label: string;
  href: string;
}

const MONITOR_ITEMS: DropdownItem[] = [
  { label: "Analytics", href: "/analytics" },
  { label: "Audit Log", href: "/audit" },
  { label: "SLA", href: "/sla" },
  { label: "Scale", href: "/scale" },
  { label: "Memory Graph", href: "/consciousness" },
];

const CONFIGURE_ITEMS: DropdownItem[] = [
  { label: "Comply", href: "/comply" },
  { label: "Profiles", href: "/profiles" },
  { label: "Webhooks", href: "/webhooks" },
  { label: "Team", href: "/team" },
];

const TOOLS_ITEMS: DropdownItem[] = [
  { label: "Code Generator", href: "/code-generator" },
  { label: "Templates", href: "/templates" },
  { label: "Protect", href: "/protect" },
  { label: "Migrate", href: "/migrate" },
  { label: "Tutorial", href: "/tutorial" },
];

function NavDropdown({ label, items, openKey, onToggle }: {
  label: string;
  items: DropdownItem[];
  openKey: string;
  onToggle: (key: string) => void;
}) {
  const isOpen = openKey === label;
  return (
    <div className="relative">
      <button
        onClick={() => onToggle(label)}
        className="flex items-center gap-1 text-muted hover:text-foreground transition text-sm"
      >
        {label}
        <span
          className="text-xs transition-transform duration-200 inline-block"
          style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          ▾
        </span>
      </button>
      {isOpen && (
        <div
          className="absolute top-full left-0 mt-2 z-50"
          style={{
            background: "#ffffff",
            borderRadius: "8px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.1)",
            padding: "8px 0",
            minWidth: "180px",
          }}
        >
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block transition-colors"
              style={{ padding: "10px 16px", fontSize: "14px", color: "#0B0F14" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "#f5f4f0";
                e.currentTarget.style.color = "#c9a962";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = "#0B0F14";
              }}
            >
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function NavBar() {
  const [apiKey, setApiKey] = useState("");
  const [copied, setCopied] = useState(false);
  const [openDropdown, setOpenDropdown] = useState("");
  const [pendingApprovals, setPendingApprovals] = useState(0);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    setApiKey(getApiKey());

    // Check for pending ASK_USER approvals
    try {
      const stored = getItem("sgraal_pending_approvals");
      if (stored) setPendingApprovals(parseInt(stored, 10) || 0);
    } catch {}
  }, []);

  // Close dropdown on outside click or Escape
  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (navRef.current && !navRef.current.contains(e.target as Node)) {
      setOpenDropdown("");
    }
  }, []);

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") setOpenDropdown("");
  }, []);

  useEffect(() => {
    document.addEventListener("click", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("click", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [handleClickOutside, handleEscape]);

  function handleToggle(key: string) {
    setOpenDropdown((prev) => (prev === key ? "" : key));
  }

  function truncateKey(key: string): string {
    if (key.length <= 16) return key;
    const prefix = key.startsWith("sg_live_") ? "sg_live_" : key.slice(0, 8);
    const rest = key.slice(prefix.length);
    return prefix + rest.slice(0, 4) + "..." + key.slice(-4);
  }

  function handleCopy() {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <nav ref={navRef} className="border-b border-surface-light px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <a href="/" className="text-lg font-bold tracking-tighter" style={{ color: "#0B0F14", fontFamily: "'Manrope', sans-serif" }}>Sgraal</a>
        <div className="flex items-center gap-5 text-sm">
          <Link href="/approvals" className="text-muted hover:text-foreground transition flex items-center gap-1.5">
            Approvals
            {pendingApprovals > 0 && (
              <span
                className="inline-flex items-center justify-center font-bold"
                style={{
                  background: "#e24b4a",
                  color: "white",
                  fontSize: "11px",
                  minWidth: "18px",
                  height: "18px",
                  borderRadius: "9px",
                  padding: "0 5px",
                  lineHeight: 1,
                }}
              >
                {pendingApprovals}
              </span>
            )}
          </Link>
          <NavDropdown label="Monitor" items={MONITOR_ITEMS} openKey={openDropdown} onToggle={handleToggle} />
          <NavDropdown label="Configure" items={CONFIGURE_ITEMS} openKey={openDropdown} onToggle={handleToggle} />
          <NavDropdown label="Tools" items={TOOLS_ITEMS} openKey={openDropdown} onToggle={handleToggle} />
          <Link href="/conflicts" className="text-muted hover:text-foreground transition">Conflicts</Link>
        </div>
      </div>
      <div className="flex items-center">
        {apiKey ? (
          <div
            className="flex items-center"
            style={{
              background: "rgba(201,169,98,0.08)",
              border: "1px solid rgba(201,169,98,0.2)",
              borderRadius: "6px",
              padding: "6px 12px",
              fontFamily: "monospace",
              fontSize: "13px",
              color: "#c9a962",
              gap: "8px",
            }}
          >
            <span>{truncateKey(apiKey)}</span>
            <button
              onClick={handleCopy}
              className="transition-colors"
              style={{ fontSize: "12px", color: copied ? "#c9a962" : "#6b7280", cursor: "pointer" }}
              onMouseEnter={(e) => { if (!copied) e.currentTarget.style.color = "#c9a962"; }}
              onMouseLeave={(e) => { if (!copied) e.currentTarget.style.color = "#6b7280"; }}
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        ) : (
          <Link
            href="/settings"
            style={{
              background: "#c9a962",
              color: "#0B0F14",
              fontWeight: 600,
              padding: "8px 16px",
              borderRadius: "6px",
              fontSize: "14px",
            }}
          >
            Get API Key &rarr;
          </Link>
        )}
      </div>
    </nav>
  );
}
