import { Hero } from "./components/sections/Hero";
import { Problem } from "./components/sections/Problem";
import { HowItWorks } from "./components/sections/HowItWorks";
import { AhaMoments } from "./components/sections/AhaMoments";
import { BattleTested } from "./components/sections/BattleTested";
import { UseCases } from "./components/sections/UseCases";
import { Integrations } from "./components/sections/Integrations";
import { Pricing } from "./components/sections/Pricing";
import { Footer } from "./components/sections/Footer";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Sgraal",
  description:
    "Memory governance protocol for AI agents. Evaluates whether agent memory is reliable before acting — returning a risk score and recommended action in under 10ms.",
  url: "https://sgraal.com",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Any",
  offers: [
    {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      description: "Free tier: 10,000 API calls per month",
    },
    {
      "@type": "Offer",
      price: "0.001",
      priceCurrency: "USD",
      description: "Usage-based: $0.001 per call after free tier",
    },
  ],
  author: {
    "@type": "Organization",
    name: "Zs-Consulting Kft.",
    url: "https://sgraal.com",
    email: "hello@sgraal.com",
  },
  license: "https://www.apache.org/licenses/LICENSE-2.0",
};

export default function Home() {
  return (
    <main className="flex-1">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <Hero />
      <Problem />
      <HowItWorks />
      <AhaMoments />
      <BattleTested />
      <UseCases />
      <Integrations />
      <Pricing />
      <Footer />
    </main>
  );
}
