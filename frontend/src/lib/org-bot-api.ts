"use client";

import { tenantAuthHeaders } from "./tenant-auth";

const API_PREFIX = "/api/v1";

export interface OrgBot {
  id: string;
  tenant_id: string;
  kb_id: string;
  title: string;
  slug: string;
  auth_mode: string;
  single_session: boolean;
  rate_limit_per_min: number;
  active: boolean;
}

export interface PublicBotInfo {
  slug: string;
  title: string;
  auth_mode: string;
  active: boolean;
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { error?: { message?: string; code?: string } };
    return data.error?.message || data.error?.code || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function listOrgBots(): Promise<OrgBot[]> {
  const response = await fetch(`${API_PREFIX}/org-bots`, {
    headers: { ...tenantAuthHeaders() },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as OrgBot[];
}

export async function createOrgBot(input: {
  kb_id: string;
  title: string;
  slug: string;
  auth_mode?: string;
  password?: string;
  single_session?: boolean;
}): Promise<OrgBot> {
  const response = await fetch(`${API_PREFIX}/org-bots`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...tenantAuthHeaders() },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as OrgBot;
}

export async function issueOrgBotOtp(
  botId: string,
  label = "",
): Promise<{ credential_id: string; otp: string; expires_at?: string }> {
  const response = await fetch(`${API_PREFIX}/org-bots/${botId}/otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...tenantAuthHeaders() },
    body: JSON.stringify({ label, ttl_minutes: 30 }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as { credential_id: string; otp: string; expires_at?: string };
}

export interface OrgBotPhone {
  id: string;
  bot_id: string;
  phone: string;
  label: string;
  active: boolean;
}

export async function listOrgBotPhones(botId: string): Promise<OrgBotPhone[]> {
  const response = await fetch(`${API_PREFIX}/org-bots/${botId}/phones`, {
    headers: { ...tenantAuthHeaders() },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as OrgBotPhone[];
}

export async function addOrgBotPhone(
  botId: string,
  phone: string,
  label = "",
): Promise<OrgBotPhone> {
  const response = await fetch(`${API_PREFIX}/org-bots/${botId}/phones`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...tenantAuthHeaders() },
    body: JSON.stringify({ phone, label }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as OrgBotPhone;
}

export async function deleteOrgBotPhone(botId: string, phoneId: string): Promise<void> {
  const response = await fetch(`${API_PREFIX}/org-bots/${botId}/phones/${phoneId}`, {
    method: "DELETE",
    headers: { ...tenantAuthHeaders() },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
}

export async function publicBotRequestOtp(slug: string, phone: string): Promise<void> {
  const response = await fetch(
    `${API_PREFIX}/public/bots/${encodeURIComponent(slug)}/otp/request`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone }),
    },
  );
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
}

export async function setOrgBotActive(botId: string, active: boolean): Promise<OrgBot> {
  const response = await fetch(`${API_PREFIX}/org-bots/${botId}/active?active=${active}`, {
    method: "POST",
    headers: { ...tenantAuthHeaders() },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as OrgBot;
}

export async function fetchPublicBot(slug: string): Promise<PublicBotInfo> {
  const response = await fetch(`${API_PREFIX}/public/bots/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as PublicBotInfo;
}

export async function publicBotLogin(
  slug: string,
  secret: string,
  username?: string,
): Promise<{ access_token: string; bot: OrgBot }> {
  const response = await fetch(`${API_PREFIX}/public/bots/${encodeURIComponent(slug)}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ secret, username: username || null }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as { access_token: string; bot: OrgBot };
}

export async function publicBotChatStream(
  slug: string,
  accessToken: string,
  prompt: string,
  onEvent: (event: string, data: Record<string, unknown>) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    `${API_PREFIX}/public/bots/${encodeURIComponent(slug)}/chat/stream`,
    {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ prompt }),
      signal,
    },
  );
  if (!response.ok || !response.body) {
    throw new Error(await parseError(response));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const block of parts) {
      let event = "message";
      let data: Record<string, unknown> = {};
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          try {
            data = JSON.parse(line.slice(5).trim()) as Record<string, unknown>;
          } catch {
            data = {};
          }
        }
      }
      onEvent(event, data);
    }
  }
}
