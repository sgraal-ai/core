const badges = ["LangChain", "CrewAI", "AutoGen", "LlamaIndex", "mem0", "MCP", "OpenAI", "Anthropic"];

export function IntegrationsBadges() {
  return (
    <section className="px-6 py-10" style={{ backgroundColor: "var(--surface-container-low)" }}>
      <div className="max-w-5xl mx-auto text-center">
        <p className="text-xs uppercase tracking-widest mb-4" style={{ fontFamily: "'Inter', sans-serif", color: "var(--on-surface-variant)", letterSpacing: "0.1em" }}>Works with</p>
        <div className="flex flex-wrap justify-center gap-3">
          {badges.map((b) => (
            <span key={b} className="px-3.5 py-1.5 rounded-full text-sm"
              style={{ backgroundColor: "var(--surface-container-lowest)", color: "var(--on-surface-variant)", border: "1px solid rgba(208,197,180,0.3)", fontFamily: "'Inter', sans-serif" }}>
              {b}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
