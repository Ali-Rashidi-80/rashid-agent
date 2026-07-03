"use client";

import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { cn } from "@/lib/cn";
import type { Locale } from "@/i18n/routing";

interface LocaleSwitcherProps {
  compact?: boolean;
}

const LOCALES: { code: Locale; label: string }[] = [
  { code: "fa", label: "فا" },
  { code: "en", label: "EN" },
];

export function LocaleSwitcher({ compact = false }: LocaleSwitcherProps) {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations("topBar");

  return (
    <div
      className={cn(
        "inline-flex rounded-lg border border-border p-1",
        compact && "text-xs",
      )}
      aria-label={t("language")}
    >
      {LOCALES.map(({ code, label }) => (
        <button
          key={code}
          type="button"
          onClick={() => router.replace(pathname, { locale: code })}
          className={cn(
            "rounded-md px-3 py-1.5 font-medium transition",
            locale === code
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
