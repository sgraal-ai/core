const badges = [
  "LangChain", "CrewAI", "AutoGen", "LlamaIndex",
  "mem0", "MCP", "OpenAI", "Anthropic",
];

export function IntegrationsBadges() {
  return (
    <section className="px-6 py-10 max-w-5xl mx-auto text-center">
      <p className="text-xs text-muted uppercase tracking-widest mb-4">Works with</p>
      <div className="flex flex-wrap justify-center gap-3">
        {badges.map((b) => (
          <span key={b} className="border border-surface-light px-4 py-1.5 rounded-full text-sm text-muted font-medium">
            {b}
          </span>
        ))}
      </div>
    </section>
  );
}
