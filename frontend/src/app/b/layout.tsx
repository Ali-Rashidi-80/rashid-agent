import "@fontsource-variable/vazirmatn";
import "../globals.css";

export default function PublicBotRootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fa" dir="rtl" className="dark" suppressHydrationWarning>
      <body
        className="min-h-screen bg-background text-foreground antialiased"
        style={
          {
            "--font-sans": "var(--font-sans-fa), system-ui, sans-serif",
          } as React.CSSProperties
        }
      >
        {children}
      </body>
    </html>
  );
}
