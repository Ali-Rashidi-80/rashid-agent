import { Inter, JetBrains_Mono, Vazirmatn } from "next/font/google";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { Toaster } from "sonner";
import { AppShell } from "@/components/shell/AppShell";
import { ThemeEngine } from "@/lib/theme-engine";
import { ThemeScript } from "@/lib/theme-script";
import { routing, type Locale } from "@/i18n/routing";
import "../globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans-en",
  display: "swap",
});

const vazirmatn = Vazirmatn({
  subsets: ["arabic", "latin"],
  variable: "--font-sans-fa",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!routing.locales.includes(locale as Locale)) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();
  const dir = locale === "fa" ? "rtl" : "ltr";
  const fontClass =
    locale === "fa"
      ? `${vazirmatn.variable} ${jetbrainsMono.variable}`
      : `${inter.variable} ${jetbrainsMono.variable}`;

  return (
    <html
      lang={locale}
      dir={dir}
      data-preset="royal-violet"
      className={`dark ${fontClass}`}
      suppressHydrationWarning
      style={
        {
          "--font-sans":
            locale === "fa"
              ? "var(--font-sans-fa), system-ui, sans-serif"
              : "var(--font-sans-en), system-ui, sans-serif",
        } as React.CSSProperties
      }
    >
      <head>
        <ThemeScript />
      </head>
      <body className="font-sans">
        <NextIntlClientProvider messages={messages}>
          <ThemeEngine />
          <AppShell>{children}</AppShell>
          <Toaster richColors position={dir === "rtl" ? "top-left" : "top-right"} />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
