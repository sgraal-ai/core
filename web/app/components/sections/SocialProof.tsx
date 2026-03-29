const stats = [
  { value: "1,834", label: "Tests passed" },
  { value: "0", label: "Failures" },
  { value: "300+", label: "Step regulated run" },
  { value: "Zero", label: "Memory drift" },
];

export function SocialProof() {
  return (
    <section style={{ backgroundColor: '#faf9f6' }}>
      <div className="max-w-4xl mx-auto px-8 md:px-16 py-24 text-center">
        <p className="text-7xl leading-none mb-4" style={{ color: 'rgba(201,169,98,0.2)' }}>&ldquo;</p>
        <blockquote className="font-headline text-3xl md:text-5xl font-bold tracking-tight mb-12 italic" style={{ color: '#1a1c1a' }}>
          Ran 300+ step regulated test with zero drift.
        </blockquote>
        <p className="font-bold mb-16" style={{ color: '#c9a962' }}>@grok</p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 py-12 mb-12"
          style={{ borderTop: '1px solid rgba(208,197,180,0.1)', borderBottom: '1px solid rgba(208,197,180,0.1)' }}>
          {stats.map((s) => (
            <div key={s.label}>
              <p className="text-2xl font-bold mb-1" style={{ color: '#c9a962' }}>{s.value}</p>
              <p className="text-[10px] uppercase tracking-widest font-bold" style={{ color: '#5e5e5e' }}>{s.label}</p>
            </div>
          ))}
        </div>

        <p className="italic font-light text-lg" style={{ color: 'rgba(94,94,94,0.6)' }}>
          When memory governance is visible, manipulation becomes accountable.
        </p>
      </div>
    </section>
  );
}
