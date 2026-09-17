import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/property-price-zones")({
  server: {
    handlers: {
      GET: async () => {
        const { priceZones } = await import("@/lib/cascade/property.server");
        return Response.json(await priceZones(), { headers: { "cache-control": "public, max-age=300" } });
      },
    },
  },
});
