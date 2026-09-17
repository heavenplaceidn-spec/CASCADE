import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/api/survey-activities")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        const { listSurveyActivities } = await import("@/lib/cascade/survey.server");
        const refresh = new URL(request.url).searchParams.get("refresh") === "1";
        const data = await listSurveyActivities({ refresh });
        return Response.json(
          {
            ok: data.ok,
            count: data.count,
            message: data.message,
            hashtag: "#geounjukkebolehan",
            source: "MAPID Survey Activity",
            type: data.fc.type,
            features: data.fc.features,
          },
          { headers: { "cache-control": refresh ? "no-store" : "public, max-age=120" } },
        );
      },
    },
  },
});
