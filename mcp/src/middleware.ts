import { SgraalClient, type PreflightRequest, type PreflightResult } from "./client.js";

export class SgraalBlockedError extends Error {
  public readonly result: PreflightResult;

  constructor(result: PreflightResult) {
    super(
      `Sgraal BLOCKED execution (Ω_MEM=${result.omega_mem_final}): ${result.explainability_note}`
    );
    this.name = "SgraalBlockedError";
    this.result = result;
  }
}

export interface GuardOptions {
  /** Sgraal API key (defaults to SGRAAL_API_KEY env var) */
  apiKey?: string;
  /** API base URL (defaults to SGRAAL_API_URL env var or https://api.sgraal.com) */
  baseUrl?: string;
  /** Called on WARN — defaults to console.warn */
  onWarn?: (result: PreflightResult) => void;
  /** Called on BLOCK before throwing — defaults to console.error */
  onBlock?: (result: PreflightResult) => void;
  /** If true, log USE_MEMORY results too */
  verbose?: boolean;
}

/**
 * Creates a guard function that runs a Sgraal preflight check.
 * - USE_MEMORY: passes through
 * - WARN / ASK_USER: logs warning, passes through
 * - BLOCK: throws SgraalBlockedError
 */
export function createGuard(options: GuardOptions = {}) {
  const client = new SgraalClient(options.apiKey, options.baseUrl);
  const onWarn = options.onWarn ?? ((r) => console.warn(`[sgraal] WARN (Ω=${r.omega_mem_final}): ${r.explainability_note}`));
  const onBlock = options.onBlock ?? ((r) => console.error(`[sgraal] BLOCK (Ω=${r.omega_mem_final}): ${r.explainability_note}`));
  const verbose = options.verbose ?? false;

  return async function guard(request: PreflightRequest): Promise<PreflightResult> {
    const result = await client.preflight(request);

    switch (result.recommended_action) {
      case "USE_MEMORY":
        if (verbose) {
          console.log(`[sgraal] USE_MEMORY (Ω=${result.omega_mem_final}): ${result.explainability_note}`);
        }
        break;
      case "WARN":
      case "ASK_USER":
        onWarn(result);
        break;
      case "BLOCK":
        onBlock(result);
        throw new SgraalBlockedError(result);
    }

    return result;
  };
}

/**
 * Wraps an async function with a Sgraal preflight check.
 * The wrapped function receives memory entries to check before executing.
 */
export function withPreflight<TArgs extends unknown[], TResult>(
  fn: (...args: TArgs) => Promise<TResult>,
  getRequest: (...args: TArgs) => PreflightRequest,
  options: GuardOptions = {},
): (...args: TArgs) => Promise<TResult> {
  const guard = createGuard(options);

  return async (...args: TArgs): Promise<TResult> => {
    await guard(getRequest(...args));
    return fn(...args);
  };
}
