import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/mapid/$")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        const { loadPreparedStyle, proxyMapidPath, proxyMapidUrl } = await import("@/lib/cascade/mapid.server");
        const url = new URL(request.url);
        const splat = String((params as { _splat?: string })._splat ?? "");
        const rest = (splat || url.pathname.replace(/^\/api\/mapid\/?/, "")).replace(/^\/+/, "");

        if (rest.startsWith("styles/")) {
          const id = rest.slice("styles/".length).split("/")[0] ?? "basic";
          const loaded = await loadPreparedStyle(id);
          if (!loaded.ok) {
            return Response.json(
              {
                error: "MAPID gagal dimuat. Periksa konfigurasi akses atau koneksi basemap.",
                stage: loaded.stage,
                status: loaded.status,
                message: loaded.message,
              },
              { status: loaded.status },
            );
          }
          return Response.json(loaded.style, { headers: { "cache-control": "public, max-age=120" } });
        }

        if (rest.startsWith("tiles/")) {
          const parts = rest.slice("tiles/".length).replace(/\.pbf$/i, "").split("/");
          const [z, x, y] = parts;
          if (![z, x, y].every((n) => n && /^\d+$/.test(n))) return new Response("Bad tile", { status: 400 });
          return proxyMapidPath(`data/mapidtiles/${z}/${x}/${y}.pbf`);
        }

        if (rest.startsWith("fonts/")) {
          const fontRest = rest.slice("fonts/".length);
          const cut = fontRest.lastIndexOf("/");
          if (cut <= 0) return new Response("Bad font", { status: 400 });
          return proxyMapidPath(`fonts/${fontRest.slice(0, cut)}/${fontRest.slice(cut + 1)}`);
        }

        if (rest === "forward" || rest.startsWith("forward")) {
          return proxyMapidUrl(url.searchParams.get("u") ?? "");
        }

        return new Response("Not found", { status: 404 });
      },
    },
  },
});
