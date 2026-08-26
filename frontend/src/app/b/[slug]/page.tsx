"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  fetchPublicBot,
  publicBotChatStream,
  publicBotLogin,
  publicBotRequestOtp,
  type PublicBotInfo,
} from "@/lib/org-bot-api";

interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

type LoginMode = "phone" | "admin";

export default function PublicBotPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [info, setInfo] = useState<PublicBotInfo | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mode, setMode] = useState<LoginMode>("phone");
  const [phone, setPhone] = useState("");
  const [secret, setSecret] = useState("");
  const [username, setUsername] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [live, setLive] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchPublicBot(slug)
      .then((bot) => {
        if (!cancelled) {
          setInfo(bot);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setLoadError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const handleRequestOtp = async () => {
    setBusy(true);
    setError(null);
    setHint(null);
    try {
      await publicBotRequestOtp(slug, phone.trim());
      setOtpSent(true);
      setHint("اگر شماره مجاز باشد، کد یک‌بارمصرف پیامک شده است. کد را وارد کنید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "otp request failed");
    } finally {
      setBusy(false);
    }
  };

  const handleLogin = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await publicBotLogin(
        slug,
        secret.trim(),
        mode === "admin" ? username.trim() || undefined : undefined,
      );
      setToken(result.access_token);
      setSecret("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "login failed");
    } finally {
      setBusy(false);
    }
  };

  const handleSend = async () => {
    if (!token || !prompt.trim() || busy) {
      return;
    }
    const question = prompt.trim();
    setPrompt("");
    setTurns((prev) => [...prev, { role: "user", content: question }]);
    setLive("");
    setBusy(true);
    setError(null);
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    let assistant = "";
    try {
      await publicBotChatStream(
        slug,
        token,
        question,
        (event, data) => {
          if (event === "message_delta" && typeof data.delta === "string") {
            assistant += data.delta;
            setLive(assistant);
          }
          if (event === "message_done" && typeof data.message === "string") {
            assistant = data.message;
            setLive(assistant);
          }
          if (event === "result" && typeof data.message === "string") {
            assistant = data.message;
            setLive(assistant);
          }
          if (event === "error" && typeof data.message === "string") {
            setError(data.message);
          }
        },
        controller.signal,
      );
      if (assistant) {
        setTurns((prev) => [...prev, { role: "assistant", content: assistant }]);
      }
      setLive("");
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError(err instanceof Error ? err.message : "stream failed");
      }
    } finally {
      setBusy(false);
    }
  };

  if (loadError) {
    return (
      <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-3 p-6">
        <h1 className="text-xl font-semibold">دستیار یافت نشد</h1>
        <p className="text-sm text-muted-foreground">{loadError}</p>
      </main>
    );
  }

  if (!info) {
    return (
      <main className="mx-auto flex min-h-screen max-w-lg items-center justify-center p-6 text-sm text-muted-foreground">
        در حال بارگذاری…
      </main>
    );
  }

  if (!token) {
    return (
      <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-4 p-6">
        <div>
          <h1 className="text-2xl font-semibold">{info.title}</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            دسترسی امن به پایگاه دانش رسمی. با شماره موبایل (در صورت مجاز بودن) یا کد ادمین وارد شوید.
          </p>
        </div>

        <div className="flex gap-2 text-sm">
          <button
            type="button"
            className={`rounded-lg px-3 py-1.5 ${mode === "phone" ? "bg-primary text-primary-foreground" : "border border-border"}`}
            onClick={() => setMode("phone")}
          >
            ورود با شماره
          </button>
          <button
            type="button"
            className={`rounded-lg px-3 py-1.5 ${mode === "admin" ? "bg-primary text-primary-foreground" : "border border-border"}`}
            onClick={() => setMode("admin")}
          >
            کد / رمز ادمین
          </button>
        </div>

        {mode === "phone" ? (
          <>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="09xxxxxxxxx"
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              dir="ltr"
            />
            <button
              type="button"
              disabled={busy || !phone.trim()}
              onClick={() => void handleRequestOtp()}
              className="rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-50"
            >
              ارسال کد پیامکی
            </button>
            {(otpSent || hint) && (
              <input
                type="text"
                inputMode="numeric"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                placeholder="کد پیامک‌شده"
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
                dir="ltr"
              />
            )}
          </>
        ) : (
          <>
            {(info.auth_mode === "password" || info.auth_mode === "both") && (
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="نام کاربری"
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            )}
            <input
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="کد یک‌بارمصرف یا رمز دسترسی"
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            />
          </>
        )}

        {hint ? <p className="text-sm text-muted-foreground">{hint}</p> : null}
        {error ? <p className="text-sm text-red-500">{error}</p> : null}
        <button
          type="button"
          disabled={busy || !secret.trim()}
          onClick={() => void handleLogin()}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          ورود امن
        </button>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-4 p-4">
      <header className="border-b border-border pb-3">
        <h1 className="text-lg font-semibold">{info.title}</h1>
        <p className="text-xs text-muted-foreground">
          پاسخ صرفاً بر اساس اسناد رسمی پایگاه دانش — بدون مشاوره خارج از اسناد
        </p>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto">
        {turns.map((turn, index) => (
          <div
            key={`${turn.role}-${index}`}
            className={`rounded-lg px-3 py-2 text-sm ${
              turn.role === "user" ? "ms-8 bg-muted/50" : "me-6 border border-border"
            }`}
          >
            <p className="mb-1 text-[10px] uppercase text-muted-foreground">
              {turn.role === "user" ? "شما" : "دستیار"}
            </p>
            <p className="whitespace-pre-wrap">{turn.content}</p>
          </div>
        ))}
        {live ? (
          <div className="me-6 rounded-lg border border-border px-3 py-2 text-sm">
            <p className="mb-1 text-[10px] uppercase text-muted-foreground">دستیار</p>
            <p className="whitespace-pre-wrap">{live}</p>
          </div>
        ) : null}
      </div>

      {error ? <p className="text-sm text-red-500">{error}</p> : null}

      <div className="flex gap-2 border-t border-border pt-3">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={2}
          placeholder="پرسش خود را بر اساس اسناد پایگاه دانش بنویسید…"
          className="min-h-[64px] flex-1 resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
        />
        <button
          type="button"
          disabled={busy || !prompt.trim()}
          onClick={() => void handleSend()}
          className="h-10 self-end rounded-lg bg-primary px-4 text-sm text-primary-foreground disabled:opacity-50"
        >
          ارسال
        </button>
      </div>
    </main>
  );
}
