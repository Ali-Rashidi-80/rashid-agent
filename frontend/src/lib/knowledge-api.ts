"use client";

import { tenantAuthHeaders } from "./tenant-auth";

const API_PREFIX = "/api/v1";

export interface KnowledgeBase {
  id: string;
  tenant_id: string;
  name: string;
  system_prompt: string;
  document_count: number;
}

export interface KbDocument {
  id: string;
  kb_id: string;
  filename: string;
  mime: string;
  size: number;
  status: string;
  error_message?: string | null;
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { error?: { message?: string; code?: string } };
    return data.error?.message || data.error?.code || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

export async function tenantLogin(username: string, password: string) {
  const response = await fetch(`${API_PREFIX}/tenants/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as {
    access_token: string;
    tenant: { id: string; slug: string; name: string };
    admin: { username: string };
  };
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  const response = await fetch(`${API_PREFIX}/knowledge-bases`, {
    headers: { ...tenantAuthHeaders() },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as KnowledgeBase[];
}

export async function createKnowledgeBase(name: string, systemPrompt = ""): Promise<KnowledgeBase> {
  const response = await fetch(`${API_PREFIX}/knowledge-bases`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...tenantAuthHeaders() },
    body: JSON.stringify({ name, system_prompt: systemPrompt }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as KnowledgeBase;
}

export async function deleteKnowledgeBase(kbId: string): Promise<void> {
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${kbId}`, {
    method: "DELETE",
    headers: { ...tenantAuthHeaders() },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
}

export async function listDocuments(kbId: string): Promise<KbDocument[]> {
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${kbId}/documents`, {
    headers: { ...tenantAuthHeaders() },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as KbDocument[];
}

export async function uploadDocuments(kbId: string, files: FileList | File[]): Promise<KbDocument[]> {
  const form = new FormData();
  for (const file of Array.from(files)) {
    form.append("files", file);
  }
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${kbId}/documents`, {
    method: "POST",
    headers: { ...tenantAuthHeaders() },
    body: form,
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as KbDocument[];
}

export async function deleteDocument(kbId: string, docId: string): Promise<void> {
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${kbId}/documents/${docId}`, {
    method: "DELETE",
    headers: { ...tenantAuthHeaders() },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
}

export async function reindexKnowledgeBase(kbId: string): Promise<KbDocument[]> {
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${kbId}/reindex`, {
    method: "POST",
    headers: { ...tenantAuthHeaders() },
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as KbDocument[];
}

export interface ErpSyncResult {
  chunks_fetched: number;
  documents_created: number;
  documents_updated: number;
  documents: KbDocument[];
}

export async function syncKnowledgeBaseFromErp(
  kbId: string,
  queries: string[],
  options?: { collections?: string[]; limit?: number; accessToken?: string },
): Promise<ErpSyncResult> {
  const response = await fetch(`${API_PREFIX}/knowledge-bases/${kbId}/erp-sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...tenantAuthHeaders() },
    body: JSON.stringify({
      queries,
      collections: options?.collections,
      limit: options?.limit ?? 8,
      access_token: options?.accessToken,
    }),
  });
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return (await response.json()) as ErpSyncResult;
}
