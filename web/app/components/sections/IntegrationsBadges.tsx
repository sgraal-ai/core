const badges = ["LangChain", "CrewAI", "AutoGen", "LlamaIndex", "mem0", "MCP", "OpenAI", "Anthropic"];

export function IntegrationsBadges() {
  return (
    <section className="bg-surface-container-low px-8 md:px-16 py-24 text-center">
      <p className="text-[10px] font-bold tracking-[0.3em] text-secondary/50 block mb-12 uppercase">Works with</p>
      <div className="flex flex-wrap justify-center gap-4">
        {badges.map((b) => (
          <span key={b} className="px-6 py-2.5 bg-surface-container-lowest border border-outline-variant/10 rounded-full text-sm font-medium text-on-surface-variant hover:border-primary-container transition-colors">
            {b}
          </span>
        ))}
      </div>
    </section>
  );
}
