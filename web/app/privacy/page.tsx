import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — Sgraal",
};

export default function PrivacyPage() {
  return (
    <main className="flex-1 max-w-3xl mx-auto px-6 py-24">
      <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
      <p className="text-muted text-sm mb-10">Last updated: March 2026</p>

      <div className="space-y-8 text-foreground/80 leading-relaxed">
        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Overview</h2>
          <p>
            Sgraal provides a memory governance protocol for AI agents. This
            policy describes how we collect, use, and protect information when
            you use the Sgraal API and website.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Information We Collect</h2>
          <p>
            When you sign up, we collect your email address and create a Stripe
            customer record for billing. API calls include memory state data
            sent for scoring — this data is processed in real time and not
            stored beyond request logging.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">How We Use Your Information</h2>
          <p>
            Your email is used for account management and billing. API usage
            data is logged for rate limiting, billing, and service improvement.
            We do not sell your data to third parties.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Data Security</h2>
          <p>
            API keys are stored as SHA-256 hashes. All API communication is
            encrypted via TLS. We follow industry best practices to protect
            your data.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-foreground mb-3">Contact</h2>
          <p>
            For privacy-related inquiries, contact us at{" "}
            <a href="mailto:hello@sgraal.com" className="text-gold hover:underline">
              hello@sgraal.com
            </a>.
          </p>
        </section>
      </div>
    </main>
  );
}
