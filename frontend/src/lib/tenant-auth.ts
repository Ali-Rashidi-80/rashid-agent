"use client";

const STORAGE_KEY = "rashid-tenant-auth";

export interface TenantAuthState {
  accessToken: string;
  tenantId: string;
  tenantSlug: string;
  username: string;
}

export function readTenantAuth(): TenantAuthState | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as TenantAuthState;
    if (!parsed.accessToken || !parsed.tenantId) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function writeTenantAuth(state: TenantAuthState): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function clearTenantAuth(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

export function tenantAuthHeaders(): HeadersInit {
  const auth = readTenantAuth();
  if (!auth) {
    return {};
  }
  return { Authorization: `Bearer ${auth.accessToken}` };
}
