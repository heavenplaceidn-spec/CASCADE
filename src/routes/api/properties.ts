import { createFileRoute } from "@tanstack/react-router";

function parseBbox(raw: string | null): [number, number, number, number] | null {
  if (!raw) return null;
  const p = raw.split(",").map(Number);
  if (p.length !== 4 || p.some((n) => !Number.isFinite(n))) return null;
  return [p[0], p[1], p[2], p[3]];
}

export const Route = createFileRoute("/api/properties")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const { listProperties } = await import("@/lib/cascade/property.server");
        const q = new URL(request.url).searchParams;
        const body = await listProperties({
          bbox: parseBbox(q.get("bbox")),
          category: q.get("category") || undefined,
          priceClass: q.get("price_class") || undefined,
          corridorType: q.get("corridor_type") || undefined,
          corridorId: q.get("corridor_id") || undefined,
          sale: q.get("sale_or_rent") || undefined,
          limit: q.get("limit") ? Number(q.get("limit")) : 250,
        });
        return Response.json(body, { headers: { "cache-control": "public, max-age=120" } });
      },
    },
  },
});
