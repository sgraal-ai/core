"use client";

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ background: "#f5f4f0", borderRadius: "8px", height: "80px", animation: "pulse 1.5s ease-in-out infinite" }} />
      ))}
      <style>{`@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
    </div>
  );
}

export function ConnectKeyState() {
  return (
    <div style={{ textAlign: "center", padding: "80px 0" }}>
      <p style={{ fontSize: "36px", color: "#c9a962", marginBottom: "12px" }}>&#x26A0;</p>
      <h3 style={{ fontSize: "20px", color: "#0B0F14", fontWeight: 700 }}>Connect your API key</h3>
      <p style={{ fontSize: "14px", color: "#6b7280", marginTop: "8px", maxWidth: "360px", margin: "8px auto 0" }}>
        Enter your API key in <a href="/settings" style={{ color: "#c9a962", textDecoration: "underline" }}>Settings</a> to see live data.
      </p>
      <p style={{ fontSize: "13px", color: "#6b7280", marginTop: "12px" }}>
        {"Don't have a key? "}
        <a href="https://sgraal.com" style={{ color: "#c9a962" }}>Get one free at sgraal.com &rarr;</a>
      </p>
    </div>
  );
}
