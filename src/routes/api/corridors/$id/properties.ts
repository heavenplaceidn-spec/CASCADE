import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/corridors/$id/properties")({
  server: {
    handlers: {
      GET: async ({ params, request }) => {
        const { listProperties } = await import("@/lib/cascade/property.server");
        const q = new URL(request.url).searchParams;
        const body = await listProperties({
          corridorId: String(params.id ?? ""),
          category: q.get("category") || undefined,
          priceClass: q.get("price_class") || undefined,
          sale: q.get("sale_or_rent") || undefined,
          limit: q.get("limit") ? Number(q.get("limit")) : 250,
        });
        return Response.json(body, { headers: { "cache-control": "public, max-age=120" } });
      },
    },
  },
});
