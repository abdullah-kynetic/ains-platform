import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { SessionProvider } from "@/components/auth/session";
import {
  companyName,
  companyUrl,
  pageDescription,
  pageTitle,
  productName,
} from "@/lib/brand";

export const metadata: Metadata = {
  title: { default: pageTitle, template: `%s · ${productName}` },
  description: pageDescription,
  applicationName: productName,
  authors: [{ name: companyName, url: companyUrl }],
  robots: { index: false, follow: false },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    siteName: companyName,
    url: companyUrl,
    type: "website",
    locale: "en_US",
  },
};
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f9" },
    { media: "(prefers-color-scheme: dark)", color: "#0d0f12" },
  ],
  colorScheme: "light dark",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('ains-theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.classList.toggle('dark',d)}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-full bg-background text-foreground">
        <a
          href="#main-content"
          className="fixed left-4 top-4 z-[100] -translate-y-24 rounded-lg bg-brand px-4 py-3 text-white focus:translate-y-0"
        >
          Skip to main content
        </a>
        <SessionProvider>
          {children}
          <Toaster />
        </SessionProvider>
      </body>
    </html>
  );
}
