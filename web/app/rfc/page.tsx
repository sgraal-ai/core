export const metadata = { title: "MemCube RFC Process — Sgraal" };

const RFCS = [
  { id: "RFC-001", title: "MemCube v2 Core Schema", status: "Implemented", version: "2.0.0",
    description: "7 required + 6 optional fields defining the standardized memory entry format." },
  { id: "RFC-002", title: "Weibull Decay per Memory Type", status: "Implemented", version: "2.0.0",
    description: "Type-specific decay rates: tool_state (fast) → identity (near-permanent)." },
  { id: "RFC-003", title: "Provenance Chain", status: "Accepted",
    description: "Optional provenance field tracking memory origin, transformations, and trust chain." },
];

export default function RFCPage() {
  return (
    <div className="max-w-3xl mx-auto py-16 px-6">
      <h1 className="text-3xl font-bold mb-4">MemCube RFC Process</h1>
      <p className="text-lg text-muted-foreground mb-8">
        Open standards for AI agent memory. Propose, review, and implement schema changes through our RFC process.
      </p>

      <div className="mb-8 p-4 bg-zinc-900 rounded-lg text-sm">
        <p className="font-mono">Draft → Review → Accepted → Implemented</p>
      </div>

      <h2 className="text-xl font-semibold mb-4">Active RFCs</h2>
      <div className="space-y-4">
        {RFCS.map((rfc) => (
          <div key={rfc.id} className="border border-zinc-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-sm text-zinc-400">{rfc.id}</span>
              <span className={`text-xs px-2 py-1 rounded ${
                rfc.status === "Implemented" ? "bg-green-900 text-green-300" :
                rfc.status === "Accepted" ? "bg-blue-900 text-blue-300" :
                "bg-yellow-900 text-yellow-300"
              }`}>{rfc.status}{rfc.version ? ` v${rfc.version}` : ""}</span>
            </div>
            <h3 className="font-semibold">{rfc.title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{rfc.description}</p>
          </div>
        ))}
      </div>

      <h2 className="text-xl font-semibold mt-10 mb-3">Propose an RFC</h2>
      <p className="text-muted-foreground mb-4">
        Open a GitHub issue with <code className="text-yellow-400">[RFC]</code> prefix. Include motivation,
        schema changes, and backward compatibility analysis. Community review: 14 days.
      </p>

      <h2 className="text-xl font-semibold mt-10 mb-3">Machine-Readable Spec</h2>
      <pre className="bg-zinc-900 p-4 rounded-lg text-sm overflow-x-auto">
{`GET /v1/standard/memcube-spec
Authorization: Bearer sg_live_...

Returns: Full JSON Schema (draft 2020-12) for MemCube v2`}
      </pre>
    </div>
  );
}
