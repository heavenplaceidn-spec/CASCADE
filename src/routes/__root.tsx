import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRootRoute, HeadContent, Outlet, Scripts } from "@tanstack/react-router";
import { useState } from "react";
import { AuthProvider } from "@/lib/auth/provider";
import { PreviewHostBridge } from "@/components/preview-host-bridge";
import { AppShell } from "@/features/app-shell";
import appCss from "../styles.css?url";

const APP_NAME = "CASCADE | MAPID WebGIS Competition 2026";

function publicShareHost() {
  const host = String(process.env.VITE_PUBLIC_HOSTNAME ?? "")
    .split(",")[0]
    .trim()
    .split(":")[0]
    .toLowerCase();
  if (!host || !/^[a-z0-9.-]+$/.test(host) || !host.includes(".")) return "";
  if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) return "";
  if (host === "vercel.app" || host.endsWith(".vercel.app") || host === "vercel.com" || host.endsWith(".vercel.com")) {
    return "";
  }
  return host;
}

export const Route = createRootRoute({
  head: () => {
    const host = publicShareHost();
    const xBanner = host ? `https://${host}/x-banner.jpg` : undefined;
    return {
      meta: [
        { charSet: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
        { title: APP_NAME },
        { name: "theme-color", content: "#07060d" },
        ...(xBanner ? [{ property: "x:game:image", content: xBanner }] : []),
      ],
      links: [
        { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
        { rel: "stylesheet", href: appCss },
        { rel: "manifest", href: "/__grok/manifest.webmanifest" },
        { rel: "apple-touch-icon", href: "/__grok/icon-180.png" },
        { rel: "prefetch", href: "/data/cascade_candidates.geojson" },
        { rel: "prefetch", href: "/data/cascade_stops.geojson" },
        { rel: "prefetch", href: "/data/krl_routes.geojson" },
        { rel: "prefetch", href: "/data/transjakarta_routes.geojson" },
        { rel: "prefetch", href: "/data/lrt_routes.geojson" },
        { rel: "prefetch", href: "/data/mrt_routes.geojson" },
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        {
          rel: "stylesheet",
          href: "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Syne:wght@600;700&display=swap",
        },
      ],
    };
  },
  component: Root,
});

function Root() {
  const [qc] = useState(() => new QueryClient());
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <HeadContent />
      </head>
      <body>
        <PreviewHostBridge />
        <AuthProvider>
          <QueryClientProvider client={qc}>
            <AppShell>
              <Outlet />
            </AppShell>
          </QueryClientProvider>
        </AuthProvider>
        <Scripts />
      </body>
    </html>
  );
}
