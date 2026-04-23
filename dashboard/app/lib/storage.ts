const isBrowser = typeof window !== "undefined";

// Use sessionStorage instead of localStorage for API keys.
// sessionStorage is cleared when the tab closes and is not accessible
// to other tabs, reducing the XSS attack window for key exfiltration.

export function getApiKey(): string {
  if (!isBrowser) return "";
  return sessionStorage.getItem("sgraal_api_key") ?? "";
}

export function setApiKey(key: string): void {
  if (!isBrowser) return;
  sessionStorage.setItem("sgraal_api_key", key);
}

export function removeApiKey(): void {
  if (!isBrowser) return;
  sessionStorage.removeItem("sgraal_api_key");
}

function _isValidApiUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname;
    return (
      hostname === "localhost" ||
      hostname === "127.0.0.1" ||
      hostname.endsWith(".sgraal.com") ||
      hostname === "sgraal.com"
    );
  } catch {
    return false;
  }
}

export function getApiUrl(): string {
  if (!isBrowser) return "https://api.sgraal.com";
  const stored = sessionStorage.getItem("sgraal_api_url");
  if (stored && _isValidApiUrl(stored)) return stored;
  return "https://api.sgraal.com";
}

export function setApiUrl(url: string): void {
  if (!isBrowser) return;
  if (!_isValidApiUrl(url)) return;
  sessionStorage.setItem("sgraal_api_url", url);
}

export function removeApiUrl(): void {
  if (!isBrowser) return;
  sessionStorage.removeItem("sgraal_api_url");
}

export function getItem(key: string): string | null {
  if (!isBrowser) return null;
  return localStorage.getItem(key);
}

export function setItem(key: string, value: string): void {
  if (!isBrowser) return;
  localStorage.setItem(key, value);
}

export function removeItem(key: string): void {
  if (!isBrowser) return;
  localStorage.removeItem(key);
}
