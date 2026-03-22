export {
  SgraalClient,
  type MemoryEntry,
  type PreflightResult,
  type PreflightRequest,
  type ActionType,
  type Domain,
} from "./client.js";

export {
  createGuard,
  withPreflight,
  SgraalBlockedError,
  type GuardOptions,
} from "./middleware.js";
