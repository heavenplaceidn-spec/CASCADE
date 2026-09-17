import { createFileRoute } from "@tanstack/react-router";
import { AnalysisPage } from "@/features/analysis-page";

export const Route = createFileRoute("/analisis")({ component: AnalysisPage });
