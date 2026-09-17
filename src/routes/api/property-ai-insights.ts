import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/property-ai-insights")({
  server: {
    handlers: {
      GET: async () => {
        const { aiInsights } = await import("@/lib/cascade/property.server");
        return Response.json(await aiInsights(), { headers: { "cache-control": "public, max-age=300" } });
      },
    },
  },
});
