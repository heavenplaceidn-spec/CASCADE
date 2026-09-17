import { SURVEY_HASHTAG, SURVEY_REJECTED, SURVEY_TITLES, SURVEY_USERS } from "./survey-allowlist";

export const SURVEY_COLOR = "#EA580C";
export const SURVEY_HASHTAG_LABEL = `#${SURVEY_HASHTAG}`;
export const SURVEY_SOURCE_LABEL = "MAPID Survey Activity";

export function normTitle(v: string) {
  return v
    .toLowerCase()
    .replace(/[#.,;:!?()[\]"'“”]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function normHashtag(v: string) {
  return v.toLowerCase().replace(/[#\s]/g, "").trim();
}

const USER_SET = new Set(SURVEY_USERS.map((u) => u.toLowerCase()));
const TITLE_SET = new Set(SURVEY_TITLES.map(normTitle));
const REJECT_SET = new Set(SURVEY_REJECTED.map(normTitle).filter((t) => t && !TITLE_SET.has(t)));

export function textHasTeamHashtag(text: string) {
  const n = normHashtag(text);
  return n.includes(SURVEY_HASHTAG);
}

export function isTeamSurvey(opts: { user?: string; title?: string; description?: string }) {
  const title = normTitle(opts.title || "");
  if (title && REJECT_SET.has(title)) return false;
  const user = String(opts.user || "").trim().toLowerCase();
  if (user && USER_SET.has(user)) return true;
  if (title && TITLE_SET.has(title)) return true;
  const blob = `${opts.title || ""} ${opts.description || ""}`;
  return textHasTeamHashtag(blob) && !!title && TITLE_SET.has(title);
}

export function surveyCategory(title: string, description: string) {
  const blob = `${title} ${description}`.toLowerCase();
  if (/(kemacetan|macet|bottleneck|mengular|padat parah|biang kerok)/.test(blob)) return "Kemacetan";
  if (/(titik strategis|kawasan strategis|potensi integrasi|simpul)/.test(blob)) return "Titik strategis";
  return "Titik Survei";
}

export function surveyCongestionHint(title: string, description: string) {
  const blob = `${title} ${description}`.toLowerCase();
  if (/(kemacetan|macet|bottleneck|mengular)/.test(blob)) return "Kemacetan / bottleneck";
  return "";
}

export function parsePhotoList(raw: unknown): string[] {
  if (Array.isArray(raw)) return raw.map((x) => String(x)).filter(Boolean);
  if (typeof raw !== "string" || !raw) return [];
  try {
    const p = JSON.parse(raw);
    return Array.isArray(p) ? p.map((x) => String(x)).filter(Boolean) : [];
  } catch {
    return raw.split("|").map((s) => s.trim()).filter(Boolean);
  }
}

export function surveyPopupRows(props: Record<string, unknown>) {
  const rows: { label: string; value: string }[] = [];
  const desc = String(props.description || "").trim();
  if (desc) rows.push({ label: "Deskripsi", value: desc.length > 220 ? `${desc.slice(0, 217)}…` : desc });
  rows.push({ label: "Hashtag", value: String(props.hashtag || SURVEY_HASHTAG_LABEL) });
  const lat = props.latitude;
  const lng = props.longitude;
  if (lat != null && lng != null) rows.push({ label: "Koordinat", value: `${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}` });
  return rows;
}
