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
            __html: `(function(){try{var t=localStorage.getItem('ains-theme');var d=t?t==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;var root=document.documentElement;root.classList.toggle('dark',d);root.dataset.theme=t==='light'||t==='dark'?t:(d?'dark':'light')}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-full bg-background text-foreground">
        <a
          href="#main-content"
          className="fixed left-4 top-4 z-[100] -translate-y-24 rounded-lg bg-accent px-4 py-3 text-on-accent focus:translate-y-0"
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
