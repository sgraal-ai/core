export const metadata = { title: "Observability — Sgraal Docs" };

export default function ObservabilityPage() {
  return (
    <div className="max-w-3xl mx-auto py-16 px-6">
      <h1 className="text-3xl font-bold mb-6">Observability</h1>
      <p className="text-lg text-muted-foreground mb-8">
        Export Sgraal traces to your observability stack — Jaeger, Zipkin, OpenTelemetry, Datadog, LangSmith, or Langfuse.
      </p>

      <h2 className="text-xl font-semibold mt-8 mb-3">Zipkin Export</h2>
      <pre className="bg-zinc-900 p-4 rounded-lg text-sm overflow-x-auto mb-6">
{`GET /v1/traces/export/zipkin
Authorization: Bearer sg_live_...

Response: { "format": "zipkin", "spans": [...] }`}
      </pre>

      <h2 className="text-xl font-semibold mt-8 mb-3">Jaeger Export</h2>
      <pre className="bg-zinc-900 p-4 rounded-lg text-sm overflow-x-auto mb-6">
{`GET /v1/traces/export/jaeger
Authorization: Bearer sg_live_...

Response: { "format": "jaeger", "data": [...] }`}
      </pre>

      <h2 className="text-xl font-semibold mt-8 mb-3">OpenTelemetry (OTLP)</h2>
      <pre className="bg-zinc-900 p-4 rounded-lg text-sm overflow-x-auto mb-6">
{`GET /v1/traces/export?format=otlp
Authorization: Bearer sg_live_...`}
      </pre>

      <h2 className="text-xl font-semibold mt-8 mb-3">Trace Propagation</h2>
      <p className="text-muted-foreground mb-4">
        Pass <code className="text-gold">trace_id</code> in your preflight request to correlate Sgraal decisions with your existing traces.
      </p>
      <pre className="bg-zinc-900 p-4 rounded-lg text-sm overflow-x-auto">
{`POST /v1/preflight
{ "trace_id": "abc123", "memory_state": [...] }`}
      </pre>
    </div>
  );
}
