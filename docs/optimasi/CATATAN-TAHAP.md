# CASCADE — catatan tahap optimasi (siap tempel)

Aplikasi: **CASCADE MAPID** (React 19 + Vite + MapLibre 6.7 + Zustand).
Sifat kerja: **patch only**. Tidak rewrite, tidak hapus fitur, tidak ubah geometri GeoJSON/SHP, tidak ubah warna koridor.

Alur akhir yang dikunci:

```
OPEN PUBLIC LINK / IG STORY
→ STARTUP LOADING (foto landscape/portrait otomatis)
→ 1% → 2% → 3% → … → 99% → 100%
→ Mulai Eksplorasi
→ SATU INSTANCE PETA
→ Eksplorasi ↔ Simulasi ↔ Analisis
→ Basic ↔ Dark ↔ Satellite
```

Setelah masuk aplikasi: loading **tidak boleh** muncul lagi kecuali user benar-benar hard-reload halaman.

---

## 0. Display-only: label koridor CASTJ

**Masalah:** popup/analisis/download hanya tampil nama rute, nomor koridor CASTJ15–CASTJ26 + Perpanjangan Koridor X tidak muncul.

**Aturan:** display-only. ID internal GeoJSON, geometry, KRL/LRT/MRT **tidak** diubah. CASTJ24 ≠ CASTJ25. CASTJ06-EXT tetap.

**Perbaikan:** mapping label publik (`corridor-label`) dipasang di popup, kartu analisis, list eksplorasi, dan download GeoJSON. Nama rute KRL/LRT/MRT tidak disentuh.

---

## 1. Integrasi Survey Activity

**Masalah:** 114 titik MAPID + allowlist Excel belum jadi layer peta.

**Perbaikan:** layer `survey-point` warna `#EA580C`, popup foto, tidak memblokir boot peta. Load survey **ditunda** setelah map interaktif (bukan syarat 100%).

---

## 2. Splash responsive: foto landscape vs portrait

**Asset yang dipakai (tidak diganti, tidak digenerate ulang):**
- `public/cascade-hero-landscape.jpg` — laptop/PC
- `public/cascade-hero-portrait.jpg` — HP portrait

**Perilaku:** deteksi otomatis viewport/orientation. Tidak ada tombol “Desktop/Mobile”. `object-fit: cover` (tidak di-stretch). Putar HP **sebelum** Mulai → foto ikut ganti. Setelah masuk app, rotasi **tidak** memunculkan loading.

---

## 3. Performa public link / Instagram / mobile

**Masalah:** orang buka dari IG Story → Safari/in-app browser. Cold start. 100 user bersamaan masing-masing parse GeoJSON + hit MAPID.

**Yang dikunci:**
- **Satu instance MapLibre** di `src/lib/cascade/map-runtime.ts` (`globalThis.__CASCADE_MAP_RUNTIME`). Unmount React **tidak** `map.remove()`. Host canvas di-park di DOM (iOS kehilangan WebGL kalau canvas dikeluarkan dari document).
- GeoJSON di-cache memori (`peekGeojson` / `loadGeojson`, `cache: "force-cache"`).
- Load bertingkat: basemap + garis existing/CASCADE dulu; stasiun, property, survey, graph, ikon kendaraan **belakangan**.
- Client sempit (iPhone / IG WebView): `pixelRatio` cap 1, `antialias: false`, `maxTileCacheSize` 40, `maxPitch: 0`.
- Ikon kendaraan **tidak** di-upload ke GPU saat boot; baru saat simulasi benar-benar jalan.
- Prefetch style MAPID (`/api/mapid/styles/{basic,dark,satellite,...}`) **setelah** 100%, tanpa WebGL kedua.

---

## 4. Progress loading 1% → 100% (bukan 10, 20, 90)

**Masalah:** angka loncat 10/20/50/80/90 lalu nyangkut 90%.

**Perbaikan di `src/features/splash.tsx`:**
- Angka visual **terpisah** dari milestone store (`loadProgress` 10/30/50/80).
- Loop `requestAnimationFrame`: +1 per tick.
- ~200 ms/tick → 99% ≈ 20 detik (target UX, **bukan** timer palsu).
- Kalau peta siap lebih cepat: sisa tick 20 ms, tetap 1% per langkah, tidak ditahan 20 detik.
- Kalau iPhone/IG lebih lama: tahan **99%** sampai core siap, baru 100%.
- **100% = peta benar-benar interaktif** (instance ada, canvas > 0, basemap siap, overlay transport bisa render).
- Property / foto survey / AI / 3D **tidak** menahan 100%.
- Tombol **Mulai Eksplorasi** disabled sampai 100%; klik hanya `splash: false`, tidak recreate map, tidak refetch.

---

## 5. Anti full-page reload (tab Simulasi/Analisis balik ke 1%)

**Akar:**
1. Tab pakai `<a href>` → Instagram WKWebView melakukan **full document load**.
2. Zustand default `splash: true` + persist kurang.
3. `GisMap` unmount memanggil `map.destroy()` / `map.remove()`.

**Perbaikan:**
- Tab = `<button type="button">` + `useNavigate()` (SPA). Sama untuk link Simulasi.
- `downloadBlob` pakai `target="_blank"` + `noopener` (iOS blob navigation).
- Error boundary per-tab. **Dilarang** `window.location.reload()` / `router.refresh()` sebagai recovery.
- Loading hanya pada **true first load** dokumen.

---

## 6. Anti black-screen / WebGL context loss (IG iPhone)

**Gejala:** UI (logo, legend, tab) hidup; canvas peta muncul 1–2 detik lalu hitam. Bukan reload.

**Akar:** WebGL context hilang (pixelRatio retina 2–3× + antialias + tekstur kendaraan + viewport IG).

**Perbaikan:**
- Listener `webglcontextlost` / `webglcontextrestored` (`preventDefault`, bukan reload).
- State renderer: `ready | degraded | recovering`.
- Soft recover: `resize` + `triggerRepaint` + rehydrate overlay dari cache.
- Hard recover: **hanya** ganti instance MapLibre di host yang sama (maks 4×/sesi). State user (tab, filter, origin/tujuan) tidak direset.
- Watchdog ~2.4 s: canvas ada, size > 0, context tidak lost.
- `visibilitychange` / `pagehide`: jeda animasi, peta tetap hidup. Kembali: resize + cek context.
- Chip non-blocking: `Memulihkan tampilan peta...` — **bukan** splash 1%.

Tes: context loss via `WEBGL_lose_context` → splash tidak kembali, `creates` tidak meledak, session JS tetap.

---

## 7. Ganti “Tampilan Peta” tanpa hilangnya koridor

**Akar:** `map.setStyle()` MAPID (terutama Basic ↔ Satellite) beda sprite/glyph → MapLibre **full rebuild** → semua custom source/layer (Existing, Masterplan, CASCADE, SHP, stasiun) terhapus, lalu di-`addLayer` lagi setelah style baru siap. Data sebenarnya **sudah di memori**.

**Perbaikan:**
- `map.setStyle(url, { diff: true, transformStyle: preserveCascadeStyle })`.
- `preserveCascadeStyle` menyalin source/layer overlay CASCADE ke style MAPID **baru sebelum commit**.
- Setelah `style.load`: kalau `candidate-mode` + `tj-existing-line` masih ada → `setData` dari cache saja. Kalau hilang → remount dari cache, **tanpa fetch GeoJSON**.
- Graph transport **tidak** di-rebuild.
- Kamera (center/zoom/bearing) di-restore kalau SDK menggeser.
- Prefetch JSON style setelah map siap.

Hasil tes: 0 request `/data/*.geojson` saat ganti basemap; 1 instance peta.

---

## 8. Rapid basemap switch (spam Basic/Dark/Satellite → canvas hitam)

**Akar:** tiap klik langsung `setStyle`. 10–20 klik = banyak transisi paralel (sprite + glyph + tile + salinan GeoJSON) → GPU/WebView KO.

**4 sabuk:**

1. **Debounce 180 ms** — yang dijalankan hanya style terakhir.
2. **Serialisasi** — `styleBusy`: maksimum 1 `setStyle` jalan. Request baru mengantri, tidak numpuk.
3. **Token `styleOp`** — callback Satellite yang telat **tidak boleh** menghapus layer Dark.
4. **Rehydrate + SHP cache** — data congestion di `mapRuntime().shpFc`. Layer visual hilang → pasang lagi dari memori. Context lost membatalkan switch, lalu recovery WebGL yang sudah ada.

Tes ekstrem 20× ganti style:
- Desktop: 22 request UI → **5** `setStyle` aktual
- Instagram UA: 22 request → **3** `setStyle`
- Koridor + SHP tetap, canvas tidak hitam, `creates = 1`, 0 refetch GeoJSON, style terakhir yang menang (`light`)

Dropdown **tidak** di-disable. Animasi kendaraan di-pause selama transisi, progress simulasi tidak di-reset.

---

## 9. Pulihkan loading screen (regresi terakhir)

**Akar:** `markAppEntered()` menulis `localStorage`/`sessionStorage` `cascade.entered=1` + boot script menyembunyikan `.landing-root`. Akibat: buka link publik / IG langsung ke peta, splash ter-skip.

**Perbaikan:**
- Flag entered **hanya** `globalThis` (umur dokumen JS). Hard reload / buka link baru = splash muncul lagi.
- Tab switch / basemap / WebGL / rotasi setelah Mulai = splash **tidak** kembali (karena SPA, bukan karena localStorage).
- Progress 1…100 + foto landscape/portrait dikembalikan.
- Loading = **gerbang masuk saja**, bukan recovery map.

Tes: desktop landscape jpg; IG portrait jpg; rotate sebelum Mulai ganti foto; setelah Mulai rotasi tidak memunculkan splash; reload halaman splash muncul lagi; rapid-basemap 26/26 tetap lulus.

---

## Arsitektur yang harus dianggap LOCKED

```
| Sistem   | Aturan                                                                         |
| -------- | ------------------------------------------------------------------------------ |
| Splash   | Hanya initial document load                                                    |
| Map      | 1 instance seumur halaman                                                      |
| Basemap  | Ganti style ≠ reload data                                                      |
| Overlay  | Existing / Masterplan / CASCADE / SHP / stasiun / survey / property dari cache |
| WebGL    | Recover in-place, dilarang `location.reload()`                                 |
| Tab      | SPA `button` + `navigate`, bukan `<a href>`                                    |
| Simulasi | Kendaraan overlay di atas SHP, tidak menggantikan SHP                          |
| Data     | Geometry, warna, CASTJ ID, KRL/LRT/MRT tidak diubah                            |
```

Hirarki render yang dikunci:

```
MAPID BASEMAP
→ SHP congestion (merah/kuning/hijau)
→ Existing / Masterplan / CASCADE
→ Stasiun
→ Survey
→ Property
→ Kendaraan
→ Popup / UI
```

---

## File inti (jangan di-rewrite)

```
| File                                | Peran                                                         |
| ----------------------------------- | ------------------------------------------------------------- |
| `src/lib/cascade/map-runtime.ts`    | Singleton peta, health, styleOp, SHP cache, recover           |
| `src/lib/cascade/device.ts`         | iPhone/IG detection, pixelRatio cap, tile cache               |
| `src/lib/cascade/store.ts`          | splash / entered in-memory, mapHealth                         |
| `src/lib/cascade/static-data.ts`    | cache GeoJSON, prefetch overlay + style                       |
| `src/lib/cascade/corridor-label.ts` | label CASTJ display-only                                      |
| `src/features/map-canvas.tsx`       | MapLibre, overlay, transformStyle, serialisasi basemap, WebGL |
| `src/features/app-shell.tsx`        | SPA tab, splash gate                                          |
| `src/features/splash.tsx`           | 1–100% + hero landscape/portrait                              |
| `src/styles.css`                    | canvas GPU layer, hero orientation                            |
| `public/cascade-hero-landscape.jpg` | splash laptop                                                 |
| `public/cascade-hero-portrait.jpg`  | splash HP                                                     |
```

---

## Yang sengaja tidak dilakukan

- Tidak matikan fitur di HP.
- Tidak percepat loading dengan angka palsu.
- Tidak reload halaman untuk “perbaiki” peta.
- Tidak recreate map tiap ganti tab/basemap.
- Tidak refetch GeoJSON/SHP saat ganti style.
- Tidak rebuild graph saat ganti basemap.
- Tidak ganti/generate ulang foto hero.
- Tidak tambah picker Desktop/Mobile.

---

## Subjek commit (versi pendek)

```
fix(cascade): splash 1–100% + portrait/landscape heroes; single MapLibre instance; WebGL in-place recovery; serialized basemap switch with overlay/SHP rehydrate from cache; no reload, no feature drop
```
