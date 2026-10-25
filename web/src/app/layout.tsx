import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { SessionProvider } from "@/components/auth/session";
import { TenantProvider } from "@/components/tenant/tenant-provider";
import { UnknownFirm } from "@/components/tenant/unknown-firm";
import {
  brandingForKnownSlug,
  firmSlugFromHost,
  safeHostLabel,
} from "@/lib/tenant";
import {
  companyName,
  companyUrl,
  pageDescription,
  pageTitle,
  productName,
} from "@/lib/brand";

const defaultMetadata: Metadata = {
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

async function requestTenant() {
  const host = (await headers()).get("host");
  return { host, tenant: firmSlugFromHost(host) };
}

export async function generateMetadata(): Promise<Metadata> {
  const { tenant } = await requestTenant();
  if (!tenant.ok) {
    return {
      title: "Unknown firm",
      description: "This address has no matching firm.",
      robots: { index: false, follow: false },
    };
  }
  const branding = brandingForKnownSlug(tenant.slug);
  if (branding.name === productName && branding.logoUrl === null) {
    return defaultMetadata;
  }
  return {
    ...defaultMetadata,
    title: { default: `${branding.name} portal`, template: `%s · ${branding.name}` },
    description: "Upload your audit documents and track their status.",
    robots: { index: false, follow: false },
  };
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { host, tenant } = await requestTenant();
  if (!tenant.ok) {
    return (
      <html lang="en" className="h-full">
        <body className="min-h-full bg-background text-foreground">
          <UnknownFirm reason={tenant.reason} host={safeHostLabel(host)} />
        </body>
      </html>
    );
  }

  const branding = brandingForKnownSlug(tenant.slug);
  return (
    <html
      lang="en"
      className="h-full"
      data-firm-slug={tenant.slug}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('ains-theme');var d=t==='dark'||(t!=='light'&&window.matchMedia('(prefers-color-scheme: dark)').matches);var root=document.documentElement;root.classList.toggle('dark',d);root.dataset.theme=t==='light'||t==='dark'?t:(d?'dark':'light')}catch(e){}})();`,
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
        <TenantProvider slug={tenant.slug} branding={branding}>
          <SessionProvider>
            {children}
            <Toaster />
          </SessionProvider>
        </TenantProvider>
      </body>
    </html>
  );
}
