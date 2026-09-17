import { createServerFn } from "@tanstack/react-start";
import { clip50 } from "./research";

const cache = new Map<string, string>();

export const explainCorridor = createServerFn({ method: "POST" })
  .validator((input: { id: string; context: string }) => input)
  .handler(async ({ data }) => {
    if (cache.has(data.id)) return { ok: true as const, text: cache.get(data.id)!, cached: true };
    const apiKey = process.env.XAI_API_KEY;
    if (!apiKey) return { ok: false as const, error: "AI tidak tersedia di lingkungan ini." };
    const res = await fetch("https://api.x.ai/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
      body: JSON.stringify({
        model: "grok-4.5",
        max_tokens: 120,
        temperature: 0.2,
        messages: [
          {
            role: "system",
            content:
              "Anda asisten decision support CASCADE. Hanya gunakan konteks yang diberi. Jangan menambah angka. Bahasa Indonesia, maksimal 50 kata. Jelaskan kenapa koridor perlu, potensi properti, dan masalah transportasi yang dibantu. Jika data kurang, katakan data belum cukup.",
          },
          { role: "user", content: data.context.slice(0, 1800) },
        ],
      }),
    });
    if (!res.ok) return { ok: false as const, error: `Layanan AI error ${res.status}` };
    const body = (await res.json()) as { choices?: { message?: { content?: string } }[] };
    const text = clip50(body.choices?.[0]?.message?.content ?? "");
    if (!text) return { ok: false as const, error: "AI tidak menghasilkan teks." };
    cache.set(data.id, text);
    return { ok: true as const, text, cached: false };
  });
