import type { Metadata, Viewport } from "next";
import { cookies } from "next/headers";
import { PreferencesSheet } from "@/components/layout/PreferencesSheet";
import { ToastProvider } from "@/components/ui/Toast";
import { PreferencesProvider } from "@/lib/i18n/PreferencesProvider";
import { LOCALE_COOKIE, localeDir, parseLocale } from "@/lib/i18n/cookies";
import { t } from "@/lib/i18n/t";
import { THEME_BOOTSTRAP_SCRIPT } from "@/lib/theme/bootstrap";
import { THEME_COOKIE } from "@/lib/theme/cookies";
import { parseThemePreference } from "@/lib/theme/resolve";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const store = await cookies();
  const locale = parseLocale(store.get(LOCALE_COOKIE)?.value);
  return {
    title: {
      default: t(locale, "meta.title"),
      template: t(locale, "meta.titleTemplate"),
    },
    description: t(locale, "meta.description"),
  };
}

export const viewport: Viewport = {
  themeColor: "#7c3aed",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const store = await cookies();
  const locale = parseLocale(store.get(LOCALE_COOKIE)?.value);
  const theme = parseThemePreference(store.get(THEME_COOKIE)?.value);

  return (
    <html lang={locale} dir={localeDir(locale)} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP_SCRIPT }} />
        <link
          rel="preload"
          href="/fonts/vazirmatn-arabic-wght-normal.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
      </head>
      <body className="min-h-dvh bg-background text-foreground antialiased">
        <PreferencesProvider locale={locale} theme={theme}>
          <ToastProvider>
            {children}
            <PreferencesSheet />
          </ToastProvider>
        </PreferencesProvider>
      </body>
    </html>
  );
}
