#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { SgraalClient, type PreflightResult } from "./client.js";

const MemoryEntrySchema = z.object({
  id: z.string(),
  content: z.string(),
  type: z.string(),
  timestamp_age_days: z.number(),
  source_trust: z.number().min(0).max(1).default(0.9),
  source_conflict: z.number().min(0).max(1).default(0.1),
  downstream_count: z.number().int().default(1),
});

function formatResult(result: PreflightResult): string {
  const icon =
    result.recommended_action === "USE_MEMORY"
      ? "PASS"
      : result.recommended_action === "BLOCK"
        ? "BLOCKED"
        : "WARNING";

  const lines = [
    `[${icon}] Ω_MEM = ${result.omega_mem_final}`,
    `Action: ${result.recommended_action}`,
    `Assurance: ${result.assurance_score}%`,
    `Reason: ${result.explainability_note}`,
    "",
    "Component Breakdown:",
    ...Object.entries(result.component_breakdown).map(
      ([k, v]) => `  ${k}: ${v}`
    ),
  ];

  return lines.join("\n");
}

async function main() {
  const client = new SgraalClient();

  const server = new McpServer({
    name: "sgraal",
    version: "0.1.0",
  });

  server.tool(
    "sgraal_preflight",
    "Check if AI agent memory is reliable enough to act on. Call this BEFORE making any decision based on stored memory. Returns USE_MEMORY (safe), WARN (proceed with caution), or BLOCK (do not proceed).",
    {
      memory_state: z.array(MemoryEntrySchema).min(1).describe(
        "Memory entries to evaluate. Each entry needs: id, content, type, timestamp_age_days, and optionally source_trust (0-1), source_conflict (0-1), downstream_count."
      ),
      action_type: z
        .enum(["informational", "reversible", "irreversible", "destructive"])
        .default("reversible")
        .describe("How critical is the action? informational < reversible < irreversible < destructive"),
      domain: z
        .enum(["general", "customer_support", "coding", "legal", "fintech", "medical"])
        .default("general")
        .describe("Domain context — higher-risk domains have stricter thresholds"),
    },
    async ({ memory_state, action_type, domain }) => {
      try {
        const result = await client.preflight({
          memory_state,
          action_type,
          domain,
        });

        const isBlocked = result.recommended_action === "BLOCK";

        return {
          content: [
            {
              type: "text" as const,
              text: formatResult(result),
            },
          ],
          isError: isBlocked,
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Sgraal preflight error: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    }
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Sgraal MCP server failed to start:", err);
  process.exit(1);
});
