"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { listKnowledgeBases, tenantLogin, type KnowledgeBase } from "@/lib/knowledge-api";
import {
  addOrgBotPhone,
  createOrgBot,
  deleteOrgBotPhone,
  issueOrgBotOtp,
  listOrgBotPhones,
  listOrgBots,
  setOrgBotActive,
  type OrgBot,
  type OrgBotPhone,
} from "@/lib/org-bot-api";
import {
  clearTenantAuth,
  readTenantAuth,
  writeTenantAuth,
  type TenantAuthState,
} from "@/lib/tenant-auth";

export function BotsPanel() {
  const t = useTranslations("bots");
  const [auth, setAuth] = useState<TenantAuthState | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [bases, setBases] = useState<KnowledgeBase[]>([]);
  const [bots, setBots] = useState<OrgBot[]>([]);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [kbId, setKbId] = useState("");
  const [botPassword, setBotPassword] = useState("");
  const [lastOtp, setLastOtp] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [phonesByBot, setPhonesByBot] = useState<Record<string, OrgBotPhone[]>>({});
  const [phoneDraft, setPhoneDraft] = useState<Record<string, string>>({});
  const [phoneLabelDraft, setPhoneLabelDraft] = useState<Record<string, string>>({});

  useEffect(() => {
    setAuth(readTenantAuth());
  }, []);

  const refresh = useCallback(async () => {
    const [kbRows, botRows] = await Promise.all([listKnowledgeBases(), listOrgBots()]);
    setBases(kbRows);
    setBots(botRows);
    if (!kbId && kbRows[0]) {
      setKbId(kbRows[0].id);
    }
    const phoneEntries = await Promise.all(
      botRows.map(async (bot) => {
        try {
          return [bot.id, await listOrgBotPhones(bot.id)] as const;
        } catch {
          return [bot.id, [] as OrgBotPhone[]] as const;
        }
      }),
    );
    setPhonesByBot(Object.fromEntries(phoneEntries));
  }, [kbId]);

  useEffect(() => {
    if (!auth) {
      return;
    }
    void refresh().catch((err: Error) => setError(err.message));
  }, [auth, refresh]);

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

  const origin = typeof window !== "undefined" ? window.location.origin : "";

  return (
    <div className="space-y-6">
      <section className="glass-panel flex flex-wrap items-center justify-between gap-3 p-4">
        <p className="text-sm text-muted-foreground">
          {auth.tenantSlug} · {auth.username}
        </p>
        <button
          type="button"
          onClick={() => {
            clearTenantAuth();
            setAuth(null);
          }}
          className="rounded-lg border border-border px-3 py-1.5 text-sm"
        >
          {t("logout")}
        </button>
      </section>

      <section className="glass-panel space-y-4 p-6">
        <h2 className="text-lg font-medium">{t("createTitle")}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t("title")}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
            placeholder={t("slug")}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
          <select
            value={kbId}
            onChange={(e) => setKbId(e.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            {bases.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name}
              </option>
            ))}
          </select>
          <input
            type="password"
            value={botPassword}
            onChange={(e) => setBotPassword(e.target.value)}
            placeholder={t("sharedPasswordOptional")}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>
        <button
          type="button"
          disabled={busy || !title.trim() || !slug.trim() || !kbId}
          onClick={() => {
            setBusy(true);
            setError(null);
            void createOrgBot({
              kb_id: kbId,
              title: title.trim(),
              slug: slug.trim(),
              auth_mode: botPassword ? "both" : "otp",
              password: botPassword || undefined,
            })
              .then(async () => {
                setTitle("");
                setSlug("");
                setBotPassword("");
                await refresh();
              })
              .catch((err: Error) => setError(err.message))
              .finally(() => setBusy(false));
          }}
          className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          {t("create")}
        </button>
      </section>

      <section className="glass-panel space-y-4 p-6">
        <h2 className="text-lg font-medium">{t("listTitle")}</h2>
        <ul className="space-y-3">
          {bots.map((bot) => {
            const link = `${origin}/b/${bot.slug}`;
            return (
              <li key={bot.id} className="space-y-2 rounded-lg border border-border p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="font-medium">{bot.title}</p>
                    <p className="text-muted-foreground">
                      {bot.slug} · {bot.active ? t("active") : t("inactive")} · {bot.auth_mode}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="rounded-md border border-border px-2 py-1 text-xs"
                      onClick={() => void navigator.clipboard.writeText(link)}
                    >
                      {t("copyLink")}
                    </button>
                    <button
                      type="button"
                      className="rounded-md border border-border px-2 py-1 text-xs"
                      onClick={() => {
                        setBusy(true);
                        void issueOrgBotOtp(bot.id, "manual")
                          .then((issued) => setLastOtp(issued.otp))
                          .catch((err: Error) => setError(err.message))
                          .finally(() => setBusy(false));
                      }}
                    >
                      {t("issueOtp")}
                    </button>
                    <button
                      type="button"
                      className="rounded-md border border-border px-2 py-1 text-xs"
                      onClick={() => {
                        void setOrgBotActive(bot.id, !bot.active)
                          .then(async () => refresh())
                          .catch((err: Error) => setError(err.message));
                      }}
                    >
                      {bot.active ? t("deactivate") : t("activate")}
                    </button>
                  </div>
                </div>
                <p className="break-all text-xs text-muted-foreground">{link}</p>
                <div className="mt-2 space-y-2 rounded-md border border-dashed border-border bg-muted/30 p-3">
                  <p className="text-sm font-medium">{t("phonesTitle")}</p>
                  <p className="text-xs text-muted-foreground">{t("phonesHint")}</p>
                  <ul className="space-y-1">
                    {(phonesByBot[bot.id] || []).map((row) => (
                      <li key={row.id} className="flex items-center justify-between gap-2 text-xs">
                        <span>
                          <code className="font-mono">{row.phone}</code>
                          {row.label ? ` · ${row.label}` : ""}
                        </span>
                        <button
                          type="button"
                          className="text-red-600"
                          onClick={() => {
                            void deleteOrgBotPhone(bot.id, row.id)
                              .then(async () => refresh())
                              .catch((err: Error) => setError(err.message));
                          }}
                        >
                          {t("removePhone")}
                        </button>
                      </li>
                    ))}
                    {!(phonesByBot[bot.id] || []).length ? (
                      <li className="text-[11px] text-muted-foreground">{t("phonesEmpty")}</li>
                    ) : null}
                  </ul>
                  <div className="flex flex-wrap gap-2">
                    <input
                      value={phoneDraft[bot.id] || ""}
                      onChange={(e) =>
                        setPhoneDraft((prev) => ({ ...prev, [bot.id]: e.target.value }))
                      }
                      placeholder={t("phonePlaceholder")}
                      className="min-w-[140px] flex-1 rounded-md border border-border bg-background px-2 py-1 text-xs"
                    />
                    <input
                      value={phoneLabelDraft[bot.id] || ""}
                      onChange={(e) =>
                        setPhoneLabelDraft((prev) => ({ ...prev, [bot.id]: e.target.value }))
                      }
                      placeholder={t("phoneLabel")}
                      className="min-w-[100px] flex-1 rounded-md border border-border bg-background px-2 py-1 text-xs"
                    />
                    <button
                      type="button"
                      className="rounded-md border border-border px-2 py-1 text-xs"
                      onClick={() => {
                        const phone = (phoneDraft[bot.id] || "").trim();
                        if (!phone) {
                          return;
                        }
                        void addOrgBotPhone(bot.id, phone, (phoneLabelDraft[bot.id] || "").trim())
                          .then(async () => {
                            setPhoneDraft((prev) => ({ ...prev, [bot.id]: "" }));
                            setPhoneLabelDraft((prev) => ({ ...prev, [bot.id]: "" }));
                            await refresh();
                          })
                          .catch((err: Error) => setError(err.message));
                      }}
                    >
                      {t("addPhone")}
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
          {!bots.length ? <li className="text-muted-foreground">{t("empty")}</li> : null}
        </ul>
        {lastOtp ? (
          <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm">
            {t("otpIssued")}: <code className="font-mono text-base">{lastOtp}</code>
          </p>
        ) : null}
      </section>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
