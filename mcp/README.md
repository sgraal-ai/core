# @sgraal/mcp

Memory governance for AI agents. Checks if memory is reliable before your agent acts.

## Install

```bash
npm install @sgraal/mcp
```

## Setup

Set your API key:

```bash
export SGRAAL_API_KEY=sg_live_...
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sgraal": {
      "command": "npx",
      "args": ["@sgraal/mcp"],
      "env": {
        "SGRAAL_API_KEY": "sg_live_..."
      }
    }
  }
}
```

Claude will have access to the `sgraal_preflight` tool and can check memory reliability before acting.

### LangGraph / Node.js

```typescript
import { createGuard } from "@sgraal/mcp";

const guard = createGuard();

// Before any memory-based decision:
const result = await guard({
  memory_state: [
    {
      id: "mem_001",
      content: "User prefers metric units",
      type: "preference_memory",
      timestamp_age_days: 45,
      source_trust: 0.9,
      source_conflict: 0.2,
      downstream_count: 3,
    },
  ],
  action_type: "irreversible",
  domain: "fintech",
});
// Throws SgraalBlockedError if BLOCK
// Logs warning if WARN
// Passes through if USE_MEMORY
```

### Wrap a function

```typescript
import { withPreflight } from "@sgraal/mcp";

const safeSendEmail = withPreflight(
  sendEmail,
  (to, subject, body, memories) => ({
    memory_state: memories,
    action_type: "irreversible",
    domain: "customer_support",
  }),
);
```

## Compatibility

Tested with @modelcontextprotocol/sdk 1.x. Breaking changes in 2.x are not guaranteed to be compatible.

## License

Apache 2.0
