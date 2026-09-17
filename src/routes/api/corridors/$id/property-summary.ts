import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/corridors/$id/property-summary")({
  server: {
    handlers: {
      GET: async ({ params }) => {
        const { corridorSummary } = await import("@/lib/cascade/property.server");
        const rec = await corridorSummary(String(params.id ?? ""));
        if (!rec) return Response.json({ error: "Ringkasan belum tersedia", data_sufficient: false }, { status: 404 });
        return Response.json(rec, { headers: { "cache-control": "public, max-age=300" } });
      },
    },
  },
});
