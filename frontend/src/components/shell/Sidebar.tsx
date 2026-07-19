"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Home, Plus, Settings } from "lucide-react";
import { Link, usePathname } from "@/i18n/navigation";
import { SessionHistory } from "@/components/shell/SessionHistory";
import { useAgentStore } from "@/lib/agent-store";
import { cn } from "@/lib/cn";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  className?: string;
}

const navItems = [
  { href: "/", icon: Home, key: "home" as const },
  { href: "/settings", icon: Settings, key: "settings" as const },
];

export function Sidebar({ open, onClose, className }: SidebarProps) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const startNewChat = useAgentStore((s) => s.startNewChat);
  const [refreshToken, setRefreshToken] = useState(0);

  const handleNewChat = () => {
    startNewChat();
    setRefreshToken((value) => value + 1);
    onClose();
  };

  return (
    <>
      {open && (
        <button
          type="button"
          aria-label="Close sidebar"
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          "z-50 flex w-64 shrink-0 flex-col border-e border-border bg-sidebar text-sidebar-foreground transition-transform lg:relative lg:translate-x-0",
          open ? "fixed inset-y-0 start-0 translate-x-0" : "fixed -translate-x-full lg:flex",
          className,
        )}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Rashid</p>
        </div>

        <div className="border-b border-border p-3">
          <button
            type="button"
            onClick={handleNewChat}
            title={`${t("newChat")} (Ctrl+Shift+N)`}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90"
          >
            <Plus className="h-4 w-4" />
            {t("newChat")}
          </button>
        </div>

        <nav className="flex flex-col gap-1 border-b border-border p-3">
          {navItems.map(({ href, icon: Icon, key }) => {
            const active = pathname === href || (href === "/" && pathname === "/");

            return (
              <Link
                key={key}
                href={href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                  active
                    ? "text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
                style={
                  active
                    ? {
                        backgroundColor:
                          "color-mix(in oklch, var(--primary) 15%, transparent)",
                      }
                    : undefined
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{t(key)}</span>
              </Link>
            );
          })}
        </nav>

        <div className="min-h-0 flex-1 overflow-y-auto py-3">
          <p className="px-4 pb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {t("history")}
          </p>
          <SessionHistory
            refreshToken={refreshToken}
            onSelectSession={onClose}
          />
        </div>
      </aside>
    </>
  );
}
