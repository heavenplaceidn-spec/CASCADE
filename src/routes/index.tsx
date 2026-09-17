import { createFileRoute } from "@tanstack/react-router";
import { ExplorePage } from "@/features/explore-page";

export const Route = createFileRoute("/")({ component: ExplorePage });
