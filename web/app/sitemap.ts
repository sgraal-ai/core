import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://sgraal.com";
  const now = new Date().toISOString();
  return [
    { url: base, lastModified: now, changeFrequency: "daily", priority: 1.0 },
    { url: `${base}/playground`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${base}/roi`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${base}/benchmark`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${base}/compatibility`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${base}/docs/compliance`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/pricing`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${base}/customers`, lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${base}/partners`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/videos`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${base}/certification`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${base}/security`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${base}/privacy`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    { url: `${base}/terms`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
  ];
}
