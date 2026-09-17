import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/properties/$id")({
  server: {
    handlers: {
      GET: async ({ params }) => {
        const { propertyById } = await import("@/lib/cascade/property.server");
        const rec = await propertyById(String(params.id ?? ""));
        if (!rec) return Response.json({ error: "Tidak ditemukan" }, { status: 404 });
        return Response.json(rec, { headers: { "cache-control": "public, max-age=120" } });
      },
    },
  },
});
