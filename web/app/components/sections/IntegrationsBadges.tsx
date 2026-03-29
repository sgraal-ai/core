const badges = ["LangChain", "CrewAI", "AutoGen", "LlamaIndex", "mem0", "MCP", "OpenAI", "Anthropic"];

export function IntegrationsBadges() {
  return (
    <section style={{ backgroundColor: '#f4f3f0' }}>
      <div className="max-w-7xl mx-auto px-8 md:px-16 py-16 text-center">
        <p className="text-[10px] font-bold tracking-[0.3em] block mb-12 uppercase" style={{ color: 'rgba(94,94,94,0.5)' }}>Works with</p>
        <div className="flex flex-wrap justify-center gap-4">
          {badges.map((b) => (
            <span key={b} className="text-sm font-medium hover:border-[#c9a962] transition-colors cursor-default"
              style={{ backgroundColor: '#ffffff', border: '1px solid rgba(208,197,180,0.3)', borderRadius: '9999px', padding: '0.5rem 1.25rem', color: '#4d4639' }}>
              {b}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
