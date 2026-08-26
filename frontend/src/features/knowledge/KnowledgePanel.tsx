"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  createKnowledgeBase,
  deleteDocument,
  deleteKnowledgeBase,
  listDocuments,
  listKnowledgeBases,
  reindexKnowledgeBase,
  syncKnowledgeBaseFromErp,
  tenantLogin,
  uploadDocuments,
  type KbDocument,
  type KnowledgeBase,
} from "@/lib/knowledge-api";
import {
  clearTenantAuth,
  readTenantAuth,
  writeTenantAuth,
  type TenantAuthState,
} from "@/lib/tenant-auth";

export function KnowledgePanel() {
  const t = useTranslations("knowledge");
  const [auth, setAuth] = useState<TenantAuthState | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [bases, setBases] = useState<KnowledgeBase[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [docs, setDocs] = useState<KbDocument[]>([]);
  const [newName, setNewName] = useState("");
  const [erpQuery, setErpQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setAuth(readTenantAuth());
  }, []);

  const refreshBases = useCallback(async () => {
    const rows = await listKnowledgeBases();
    setBases(rows);
    if (rows.length && !selectedId) {
      setSelectedId(rows[0].id);
    }
  }, [selectedId]);

  const refreshDocs = useCallback(async (kbId: string) => {
    setDocs(await listDocuments(kbId));
  }, []);

  useEffect(() => {
    if (!auth) {
      return;
    }
    void refreshBases().catch((err: Error) => setError(err.message));
  }, [auth, refreshBases]);

  useEffect(() => {
    if (!auth || !selectedId) {
      setDocs([]);
      return;
    }
    void refreshDocs(selectedId).catch((err: Error) => setError(err.message));
  }, [auth, selectedId, refreshDocs]);

  const handleLogin = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await tenantLogin(username.trim(), password);
      const next: TenantAuthState = {
        accessToken: result.access_token,
        tenantId: result.tenant.id,
        tenantSlug: result.tenant.slug,
        username: result.admin.username,
      };
      writeTenantAuth(next);
      setAuth(next);
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "login failed");
    } finally {
      setBusy(false);
    }
  };

  const handleLogout = () => {
    clearTenantAuth();
    setAuth(null);
    setBases([]);
    setDocs([]);
    setSelectedId(null);
  };

  if (!auth) {
    return (
      <section className="glass-panel space-y-4 p-6">
        <div>
          <h2 className="text-lg font-medium">{t("loginTitle")}</h2>
          <p className="text-sm text-muted-foreground">{t("loginDesc")}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={t("username")}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t("password")}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button
          type="button"
          disabled={busy || !username || !password}
          onClick={() => void handleLogin()}
          className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          {t("login")}
        </button>
      </section>
    );
  }

  return (
    <div className="space-y-6">
      <section className="glass-panel flex flex-wrap items-center justify-between gap-3 p-4">
        <p className="text-sm text-muted-foreground">
          {auth.tenantSlug} · {auth.username}
        </p>
        <button
          type="button"
          onClick={handleLogout}
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
        >
          {t("logout")}
        </button>
      </section>

      <section className="glass-panel space-y-4 p-6">
        <h2 className="text-lg font-medium">{t("basesTitle")}</h2>
        <div className="flex flex-wrap gap-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={t("newBaseName")}
            className="min-w-[200px] flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
          <button
            type="button"
            disabled={busy || !newName.trim()}
            onClick={() => {
              setBusy(true);
              void createKnowledgeBase(newName.trim())
                .then(async (kb) => {
                  setNewName("");
                  setSelectedId(kb.id);
                  await refreshBases();
                })
                .catch((err: Error) => setError(err.message))
                .finally(() => setBusy(false));
            }}
            className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
          >
            {t("createBase")}
          </button>
        </div>
        <ul className="space-y-2">
          {bases.map((kb) => (
            <li key={kb.id} className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2">
              <button
                type="button"
                onClick={() => setSelectedId(kb.id)}
                className={`text-start text-sm ${selectedId === kb.id ? "text-primary" : ""}`}
              >
                {kb.name}{" "}
                <span className="text-muted-foreground">({kb.document_count})</span>
              </button>
              <button
                type="button"
                className="text-xs text-red-600"
                onClick={() => {
                  void deleteKnowledgeBase(kb.id)
                    .then(async () => {
                      if (selectedId === kb.id) {
                        setSelectedId(null);
                      }
                      await refreshBases();
                    })
                    .catch((err: Error) => setError(err.message));
                }}
              >
                {t("delete")}
              </button>
            </li>
          ))}
        </ul>
      </section>

      {selectedId ? (
        <section className="glass-panel space-y-4 p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-medium">{t("docsTitle")}</h2>
            <div className="flex gap-2">
              <label className="cursor-pointer rounded-lg border border-border px-3 py-1.5 text-sm">
                {t("upload")}
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(event) => {
                    const files = event.target.files;
                    if (!files?.length) {
                      return;
                    }
                    setBusy(true);
                    void uploadDocuments(selectedId, files)
                      .then(async () => {
                        await refreshDocs(selectedId);
                        await refreshBases();
                      })
                      .catch((err: Error) => setError(err.message))
                      .finally(() => setBusy(false));
                    event.target.value = "";
                  }}
                />
              </label>
              <button
                type="button"
                className="rounded-lg border border-border px-3 py-1.5 text-sm"
                onClick={() => {
                  setBusy(true);
                  void reindexKnowledgeBase(selectedId)
                    .then(async () => refreshDocs(selectedId))
                    .catch((err: Error) => setError(err.message))
                    .finally(() => setBusy(false));
                }}
              >
                {t("reindex")}
              </button>
            </div>
          </div>
          <div className="space-y-2 rounded-lg border border-dashed border-border p-3">
            <p className="text-xs text-muted-foreground">{t("erpSyncHint")}</p>
            <div className="flex flex-wrap gap-2">
              <input
                value={erpQuery}
                onChange={(e) => setErpQuery(e.target.value)}
                placeholder={t("erpSyncQuery")}
                className="min-w-[220px] flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
              <button
                type="button"
                disabled={busy || !erpQuery.trim()}
                className="rounded-lg border border-border px-3 py-1.5 text-sm disabled:opacity-50"
                onClick={() => {
                  setBusy(true);
                  setError(null);
                  void syncKnowledgeBaseFromErp(selectedId, [erpQuery.trim()])
                    .then(async () => {
                      await refreshDocs(selectedId);
                      await refreshBases();
                    })
                    .catch((err: Error) => setError(err.message))
                    .finally(() => setBusy(false));
                }}
              >
                {t("erpSync")}
              </button>
            </div>
          </div>
          <ul className="space-y-2">
            {docs.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-sm">
                <span>
                  {doc.filename}{" "}
                  <span className="text-muted-foreground">· {doc.status}</span>
                  {doc.error_message ? (
                    <span className="ms-2 text-red-600">{doc.error_message}</span>
                  ) : null}
                </span>
                <button
                  type="button"
                  className="text-xs text-red-600"
                  onClick={() => {
                    void deleteDocument(selectedId, doc.id)
                      .then(async () => {
                        await refreshDocs(selectedId);
                        await refreshBases();
                      })
                      .catch((err: Error) => setError(err.message));
                  }}
                >
                  {t("delete")}
                </button>
              </li>
            ))}
            {!docs.length ? (
              <li className="text-sm text-muted-foreground">{t("noDocs")}</li>
            ) : null}
          </ul>
        </section>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
