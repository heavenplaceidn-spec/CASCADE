import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/corridors/$id/price-distribution")({
  server: {
    handlers: {
      GET: async ({ params }) => {
        const { corridorSummary } = await import("@/lib/cascade/property.server");
        const rec = await corridorSummary(String(params.id ?? ""));
        if (!rec) return Response.json({ error: "Distribusi belum tersedia", data_sufficient: false }, { status: 404 });
        return Response.json(
          {
            corridor_id: rec.corridor_id,
            murah_pct: rec.murah_pct,
            sedang_pct: rec.sedang_pct,
            mahal_pct: rec.mahal_pct,
            median_price: rec.median_price,
            median_price_per_m2: rec.median_price_per_m2,
            property_count: rec.property_count,
            data_sufficient: rec.data_sufficient,
          },
          { headers: { "cache-control": "public, max-age=300" } },
        );
      },
    },
  },
});
