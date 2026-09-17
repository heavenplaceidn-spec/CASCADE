import { createFileRoute } from "@tanstack/react-router";
import { SimulatePage } from "@/features/simulate-page";

export const Route = createFileRoute("/simulasi")({ component: SimulatePage });
