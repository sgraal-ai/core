// n8n Sgraal Preflight Node
export const nodeDefinition = {
  displayName: "Sgraal Preflight",
  name: "sgraalPreflight",
  group: ["transform"],
  version: 1,
  inputs: ["main"],
  outputs: ["main"],
  properties: [
    { displayName: "API Key", name: "apiKey", type: "string", default: "" },
    { displayName: "Domain", name: "domain", type: "string", default: "general" },
  ],
};
