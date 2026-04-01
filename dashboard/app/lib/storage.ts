const isBrowser = typeof window !== "undefined";

export function getApiKey(): string {
  if (!isBrowser) return "";
  return localStorage.getItem("sgraal_api_key") ?? "";
}

export function setApiKey(key: string): void {
  if (!isBrowser) return;
  localStorage.setItem("sgraal_api_key", key);
}

export function removeApiKey(): void {
  if (!isBrowser) return;
  localStorage.removeItem("sgraal_api_key");
}

export function getApiUrl(): string {
  if (!isBrowser) return "https://api.sgraal.com";
  return localStorage.getItem("sgraal_api_url") ?? "https://api.sgraal.com";
}

export function setApiUrl(url: string): void {
  if (!isBrowser) return;
  localStorage.setItem("sgraal_api_url", url);
}

export function removeApiUrl(): void {
  if (!isBrowser) return;
  localStorage.removeItem("sgraal_api_url");
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
