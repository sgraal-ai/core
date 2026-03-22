import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service — Sgraal",
};

export default function TermsPage() {
  return (
    <main className="flex-1 max-w-3xl mx-auto px-6 py-24">
      <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
      <p className="text-muted text-sm mb-10">Last updated: March 2026</p>

      <div className="space-y-8 text-foreground/80 leading-relaxed">
        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Acceptance of Terms</h2>
          <p>
            By accessing or using the Sgraal memory governance protocol API,
            you agree to be bound by these terms. If you do not agree, do not
            use the service.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Service Description</h2>
          <p>
            Sgraal provides a preflight scoring API that evaluates the
            reliability of AI agent memory states. The service returns risk
            scores and recommended actions (USE_MEMORY, WARN, ASK_USER, BLOCK)
            to help agents make safer decisions.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">API Usage</h2>
          <p>
            You are responsible for securing your API key. Do not share it
            publicly or embed it in client-side code. Usage is subject to the
            rate limits of your plan tier (free: 10,000 calls/month). Exceeding
            limits will result in HTTP 429 responses.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Disclaimer</h2>
          <p>
            Sgraal provides memory risk scores as advisory information. The
            service does not guarantee the accuracy of memory data you submit.
            You are responsible for the decisions your AI agents make based on
            Sgraal scores.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">License</h2>
          <p>
            The Sgraal protocol is licensed under Apache 2.0 — open protocol,
            free to use and embed.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Contact</h2>
          <p>
            For questions about these terms, contact us at{" "}
            <a href="mailto:hello@sgraal.com" className="text-gold hover:underline">
              hello@sgraal.com
            </a>.
          </p>
        </section>
      </div>
    </main>
  );
}
