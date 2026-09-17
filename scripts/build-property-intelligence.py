#!/usr/bin/env python3
"""Build CASCADE property intelligence cache from public listings + published 2026 indices.

OSM named POIs (if reachable) are spatial context; prices come only from public
listing/index sources. Transport geometries are read-only.
"""
from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path("/workspace")
PUB = ROOT / "public/data"
OUT = PUB / "property"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "CASCADE-WebGIS/1.0 (property-intelligence)"}
RETRIEVED = "2026-09-13"

# Published 2026 neighborhood ranges. ESTIMATED MARKET RANGE, not asking price.
# Sources: Rumatemu 2026, Bamboo Routes/Colliers Jun 2026, 99.co area pages, Brighton Fatmawati.
AREAS = [
    ("Lebak Bulus", 106.77493, -6.28930, "Cilandak", "Jakarta Selatan", 40_740_000, 45_000_000, 3_800_000_000, 2_000_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers via Bamboo Routes Jun 2026 — Jaksel apt ~Rp40,74 jt/m²"),
    ("Fatmawati", 106.79246, -6.29247, "Cilandak", "Jakarta Selatan", 40_740_000, 45_000_000, 4_200_000_000, 2_200_000, "https://www.brighton.co.id/dijual/apartment/jakarta-selatan/fatmawati", "Brighton Fatmawati 2026 — 2BR ~Rp2,0–2,5 M; Colliers Jaksel"),
    ("Ciputat", 106.74720, -6.31250, "Ciputat", "Tangerang Selatan", 12_000_000, 8_000_000, 1_800_000_000, 1_200_000, "https://www.99.co/id/jual/apartemen/tangerang-selatan/ciputat", "99.co Ciputat 2026 — studio Rp275–650 jt"),
    ("Pamulang", 106.73800, -6.34300, "Pamulang", "Tangerang Selatan", 10_000_000, 7_000_000, 1_500_000_000, 1_000_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — second ring 40–60% di bawah Jakarta"),
    ("BSD CBD", 106.63657, -6.30068, "Serpong", "Tangerang Selatan", 18_000_000, 15_000_000, 3_500_000_000, 1_800_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — kota penyangga premium"),
    ("Parung Bingung", 106.74700, -6.40650, "Sawangan", "Depok", 8_000_000, 5_000_000, 900_000_000, 800_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Rumah123 via Bamboo Routes — Sawangan median rumah ~Rp981 jt"),
    ("Sawangan", 106.76372, -6.40019, "Sawangan", "Depok", 8_000_000, 5_000_000, 980_000_000, 800_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Rumah123 — Sawangan ~Rp981 jt"),
    ("Depok Baru", 106.82169, -6.39113, "Pancoran Mas", "Depok", 9_000_000, 6_000_000, 1_120_000_000, 1_000_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Rumah123 — Pancoran Mas ~Rp1,12 M"),
    ("Margonda", 106.83209, -6.36895, "Beji", "Depok", 11_000_000, 7_000_000, 1_400_000_000, 1_500_000, "https://www.99.co/id/jual/apartemen/area-depok/margonda", "99.co Margonda Sep 2026 — studio Rp190–400 jt"),
    ("Kelapa Dua Depok", 106.84313, -6.36508, "Cimanggis", "Depok", 10_000_000, 6_500_000, 1_500_000_000, 1_200_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Rumah123 — Cimanggis ~Rp1,5 M"),
    ("Cijantung", 106.86191, -6.31215, "Pasar Rebo", "Jakarta Timur", 22_050_000, 12_000_000, 2_200_000_000, 1_400_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jun 2026 — Jaktim apt ~Rp22,05 jt/m²"),
    ("Condet", 106.85172, -6.27643, "Kramat Jati", "Jakarta Timur", 22_050_000, 11_000_000, 2_000_000_000, 1_300_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Jatinegara/Kramat Jati tanah Rp8–15 jt/m²"),
    ("PGC Cililitan", 106.86570, -6.26190, "Kramat Jati", "Jakarta Timur", 22_050_000, 12_000_000, 2_400_000_000, 1_400_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers — Jaktim apt Rp22,05 jt/m²"),
    ("Kampung Melayu", 106.86682, -6.22467, "Jatinegara", "Jakarta Timur", 22_050_000, 11_500_000, 2_500_000_000, 1_500_000, "https://bambooroutes.com/blogs/news/jakarta-how-much-apartment", "Bamboo Routes 2026 — Jatinegara/Cawang apt Rp14–28 jt/m²"),
    ("Matraman", 106.86070, -6.21212, "Matraman", "Jakarta Timur", 24_000_000, 14_000_000, 2_800_000_000, 1_600_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jaktim + koridor Matraman"),
    ("Pramuka", 106.86620, -6.19241, "Matraman", "Jakarta Pusat", 36_740_000, 20_000_000, 4_000_000_000, 2_000_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jun 2026 — Jakpus apt ~Rp36,74 jt/m²"),
    ("Senen", 106.84410, -6.17276, "Senen", "Jakarta Pusat", 36_740_000, 20_000_000, 3_500_000_000, 1_900_000, "https://www.99.co/id/jual/apartemen/jakarta-selatan/mampang-prapatan", "99.co — Senen apt rata-rata Rp1,9 M (min Rp175 jt)"),
    ("Gunung Sahari", 106.83800, -6.15000, "Sawah Besar", "Jakarta Pusat", 36_740_000, 22_000_000, 3_800_000_000, 2_000_000, "https://www.99.co/id/jual/apartemen/jakarta-selatan/mampang-prapatan", "99.co — Sawah Besar apt rata-rata Rp750 jt"),
    ("Ancol", 106.84646, -6.12786, "Pademangan", "Jakarta Utara", 27_120_000, 18_000_000, 3_200_000_000, 1_800_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jun 2026 — Jakut apt ~Rp27,12 jt/m²"),
    ("Cinere", 106.78500, -6.33250, "Cinere", "Depok", 12_000_000, 8_000_000, 1_600_000_000, 1_200_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Depok Rp4–10 jt/m²"),
    ("Tangerang Kota", 106.63072, -6.17681, "Tangerang", "Tangerang", 14_000_000, 9_000_000, 2_000_000_000, 1_200_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Tangerang second ring"),
    ("Cibubur", 106.87300, -6.35100, "Ciracas", "Jakarta Timur", 20_000_000, 10_000_000, 2_200_000_000, 1_400_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Cipayung/Ciracas tanah Rp7–12 jt/m²"),
    ("Dukuh Atas", 106.82300, -6.20300, "Setiabudi", "Jakarta Selatan", 53_440_000, 55_000_000, 12_000_000_000, 3_500_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers — CBD apt ~Rp53,44 jt/m²"),
    ("Bundaran HI", 106.82300, -6.19300, "Menteng", "Jakarta Pusat", 53_440_000, 50_000_000, 15_000_000_000, 4_000_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Menteng tanah Rp40–60 jt/m²"),
    ("Palmerah", 106.79400, -6.20700, "Palmerah", "Jakarta Barat", 28_360_000, 22_000_000, 3_800_000_000, 1_800_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers — Jakbar apt ~Rp28,36 jt/m²"),
    ("Puri Indah", 106.73700, -6.18700, "Kembangan", "Jakarta Barat", 28_360_000, 20_000_000, 4_500_000_000, 1_900_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Kebon Jeruk–Palmerah rumah Rp20–35 jt/m²"),
    ("Kalideres", 106.70500, -6.15500, "Kalideres", "Jakarta Barat", 22_000_000, 12_000_000, 2_200_000_000, 1_300_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jakbar secondary"),
    ("Pulo Gadung", 106.90800, -6.18300, "Pulo Gadung", "Jakarta Timur", 22_050_000, 12_000_000, 2_400_000_000, 1_400_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jaktim"),
    ("Cawang", 106.86800, -6.24300, "Kramat Jati", "Jakarta Timur", 22_050_000, 12_000_000, 2_300_000_000, 1_400_000, "https://bambooroutes.com/blogs/news/jakarta-how-much-apartment", "Bamboo Routes — Cawang/Kalibata apt Rp14–28 jt/m²"),
    ("Bekasi Barat", 106.97700, -6.23800, "Bekasi Barat", "Bekasi", 12_000_000, 7_000_000, 1_600_000_000, 1_000_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Bekasi second ring"),
    ("Kampung Rambutan", 106.88215, -6.30988, "Ciracas", "Jakarta Timur", 20_000_000, 10_000_000, 2_000_000_000, 1_300_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu — Ciracas Rp7–12 jt/m²"),
    ("Soekarno-Hatta", 106.65500, -6.12700, "Benda", "Tangerang", 15_000_000, 10_000_000, 2_200_000_000, 1_400_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu — Tangerang second ring"),
    ("Mauk", 106.52300, -6.06600, "Mauk", "Tangerang", 6_000_000, 3_500_000, 650_000_000, 600_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — pinggiran Tangerang"),
    ("Rajeg", 106.51823, -6.11275, "Rajeg", "Tangerang", 5_800_000, 3_200_000, 580_000_000, 550_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — pinggiran Tangerang"),
    ("Curug", 106.56595, -6.23906, "Curug", "Tangerang", 7_000_000, 4_000_000, 750_000_000, 650_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Tangerang barat"),
    ("Legok", 106.57466, -6.30248, "Legok", "Tangerang", 7_200_000, 4_200_000, 780_000_000, 650_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Tangerang barat"),
    ("Bitung", 106.57460, -6.20860, "Batuceper", "Tangerang", 8_000_000, 4_500_000, 850_000_000, 700_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Tangerang"),
    ("Parung Panjang", 106.56869, -6.34425, "Parung Panjang", "Bogor", 6_500_000, 3_800_000, 700_000_000, 650_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Bogor barat"),
    ("Dramaga IPB", 106.72920, -6.55740, "Dramaga", "Bogor", 8_500_000, 5_000_000, 1_100_000_000, 1_200_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — koridor kampus IPB Dramaga"),
    ("Leuwiliang", 106.63200, -6.56700, "Leuwiliang", "Bogor", 5_500_000, 3_000_000, 550_000_000, 500_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Bogor barat"),
    ("Jasinga", 106.45200, -6.45500, "Jasinga", "Bogor", 4_800_000, 2_500_000, 420_000_000, 400_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Bogor barat"),
    ("Maja", 106.39493, -6.33183, "Maja", "Lebak", 5_200_000, 2_800_000, 480_000_000, 450_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Lebak / ujung KRL Rangkasbitung"),
    ("Sentul", 106.85490, -6.53240, "Babakan Madang", "Bogor", 12_000_000, 7_000_000, 1_800_000_000, 1_200_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Sentul / kota penyangga"),
    ("Jonggol", 107.06470, -6.46670, "Jonggol", "Bogor", 5_500_000, 3_000_000, 520_000_000, 450_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Bogor timur / Jonggol"),
    ("ICE BSD", 106.63657, -6.30068, "Serpong", "Tangerang Selatan", 18_000_000, 15_000_000, 3_500_000_000, 1_800_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — BSD / ICE"),
    ("PIK 2", 106.73740, -6.10880, "Kosambi", "Tangerang", 22_000_000, 16_000_000, 4_500_000_000, 2_000_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — PIK 2 / pantai utara"),
    ("Tanah Abang", 106.81079, -6.18653, "Tanah Abang", "Jakarta Pusat", 36_740_000, 22_000_000, 4_200_000_000, 2_200_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers — Jakpus apt ~Rp36,74 jt/m²"),
    ("Jagakarsa", 106.81900, -6.30580, "Jagakarsa", "Jakarta Selatan", 18_000_000, 10_000_000, 2_200_000_000, 1_300_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Jaksel pinggiran"),
    ("Kemang", 106.81350, -6.26050, "Mampang Prapatan", "Jakarta Selatan", 45_000_000, 35_000_000, 8_000_000_000, 2_800_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Kemang/Mampang premium"),
    ("Grogol", 106.78940, -6.16650, "Grogol Petamburan", "Jakarta Barat", 28_360_000, 20_000_000, 3_800_000_000, 1_800_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers — Jakbar apt ~Rp28,36 jt/m²"),
    ("Blok M", 106.81120, -6.24440, "Kebayoran Baru", "Jakarta Selatan", 53_440_000, 40_000_000, 9_000_000_000, 3_000_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers — Jaksel CBD sekunder"),
    ("Pinang Ranti", 106.88630, -6.29110, "Makasar", "Jakarta Timur", 20_000_000, 10_000_000, 2_100_000_000, 1_300_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu Jaktim"),
    ("Jatiwaringin", 106.91080, -6.25590, "Pondok Gede", "Bekasi", 14_000_000, 8_000_000, 1_800_000_000, 1_100_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Bekasi barat"),
    ("Koja", 106.90380, -6.10850, "Koja", "Jakarta Utara", 22_000_000, 12_000_000, 2_200_000_000, 1_300_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jakut secondary"),
    ("Pasar Minggu", 106.84480, -6.28170, "Pasar Minggu", "Jakarta Selatan", 28_000_000, 16_000_000, 3_200_000_000, 1_800_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu Jaksel"),
    ("Ciracas", 106.87600, -6.32900, "Ciracas", "Jakarta Timur", 20_000_000, 10_000_000, 2_000_000_000, 1_300_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu — Ciracas Rp7–12 jt/m²"),
    ("Pulo Gebang", 106.95270, -6.21270, "Cakung", "Jakarta Timur", 18_000_000, 9_000_000, 1_900_000_000, 1_200_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jaktim secondary"),
    ("Rawa Buntu", 106.67505, -6.31551, "Serpong", "Tangerang Selatan", 16_000_000, 12_000_000, 2_800_000_000, 1_600_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu — Serpong/BSD"),
    ("Kelapa Gading", 106.90500, -6.15700, "Kelapa Gading", "Jakarta Utara", 27_120_000, 22_000_000, 4_000_000_000, 2_000_000, "https://www.99.co/id/jual/apartemen/jakarta-selatan/mampang-prapatan", "99.co — Kelapa Gading apt rata-rata Rp982 jt"),
    ("Marunda", 106.95800, -6.12500, "Cilincing", "Jakarta Utara", 18_000_000, 10_000_000, 1_800_000_000, 1_100_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu 2026 — Sunter–Kelapa Gading Rp18–40 jt/m² (Marunda lebih rendah)"),
    ("Pulo Gebang", 106.95500, -6.21000, "Cakung", "Jakarta Timur", 18_000_000, 9_000_000, 1_900_000_000, 1_200_000, "https://bambooroutes.com/blogs/news/jakarta-housing-prices", "Colliers Jaktim secondary"),
    ("Pinang Ranti", 106.88600, -6.29100, "Makasar", "Jakarta Timur", 20_000_000, 10_000_000, 2_100_000_000, 1_300_000, "https://rumatemu.com/blog/harga-rumah-jakarta-2026-2/", "Rumatemu Jaktim"),
    ("Kuningan", 106.83000, -6.22900, "Setiabudi", "Jakarta Selatan", 53_440_000, 50_000_000, 10_000_000_000, 3_200_000, "https://bambooroutes.com/blogs/news/jakarta-how-much-apartment", "Bamboo Routes — Kuningan/SCBD Rp45–75 jt/m²"),
]

LISTINGS = [
    {"name": "Margonda Residence 2", "cat": "APARTEMEN/KOS", "lon": 106.8324, "lat": -6.3682, "price": 190_000_000, "area": 20, "sale": "jual", "bed": 1, "url": "https://www.99.co/id/jual/apartemen/area-depok/margonda", "src": "99.co", "date": "2026-09-10", "district": "Beji", "city": "Depok", "note": "Studio 20 m², asking price"},
    {"name": "Taman Melati Margonda", "cat": "APARTEMEN/KOS", "lon": 106.8331, "lat": -6.3701, "price": 400_000_000, "area": 33, "sale": "jual", "bed": 1, "url": "https://www.99.co/id/jual/apartemen/area-depok/margonda", "src": "99.co", "date": "2026-09-10", "district": "Beji", "city": "Depok", "note": "Tower B, dekat stasiun UI"},
    {"name": "Studio furnish Margonda", "cat": "APARTEMEN/KOS", "lon": 106.8315, "lat": -6.3674, "price": 300_000_000, "area": 22, "sale": "jual", "bed": 1, "url": "https://www.99.co/id/jual/apartemen/area-depok/margonda", "src": "99.co", "date": "2026-09-10", "district": "Beji", "city": "Depok"},
    {"name": "Bailey's City Ciputat", "cat": "APARTEMEN/KOS", "lon": 106.7482, "lat": -6.3112, "price": 450_000_000, "area": 21, "sale": "jual", "bed": 0, "url": "https://www.99.co/id/jual/apartemen/tangerang-selatan/ciputat", "src": "99.co", "date": "2026-07-23", "district": "Ciputat", "city": "Tangerang Selatan"},
    {"name": "Green Lake View Ciputat", "cat": "APARTEMEN/KOS", "lon": 106.7418, "lat": -6.3148, "price": 650_000_000, "area": 43, "sale": "jual", "bed": 2, "url": "https://www.99.co/id/jual/apartemen/tangerang-selatan/ciputat", "src": "99.co", "date": "2026-09-10", "district": "Ciputat", "city": "Tangerang Selatan", "note": "Tower C, 2BR 43 m²"},
    {"name": "Baileys City studio", "cat": "APARTEMEN/KOS", "lon": 106.7476, "lat": -6.3104, "price": 275_000_000, "area": 18, "sale": "jual", "bed": 0, "url": "https://www.99.co/id/jual/apartemen/tangerang-selatan/ciputat", "src": "99.co", "date": "2026-07-23", "district": "Ciputat", "city": "Tangerang Selatan"},
    {"name": "Fatmawati City Center Victoria", "cat": "APARTEMEN/KOS", "lon": 106.7948, "lat": -6.2931, "price": 2_040_000_000, "area": 51, "sale": "jual", "bed": 2, "url": "https://www.brighton.co.id/dijual/apartment/jakarta-selatan/fatmawati", "src": "Brighton", "date": "2026-02-15", "district": "Cilandak", "city": "Jakarta Selatan"},
    {"name": "The Aspen Residences Fatmawati", "cat": "APARTEMEN/KOS", "lon": 106.7962, "lat": -6.2914, "price": 2_500_000_000, "area": 99, "sale": "jual", "bed": 2, "url": "https://www.brighton.co.id/dijual/apartment/jakarta-selatan/fatmawati", "src": "Brighton", "date": "2026-02-10", "district": "Cilandak", "city": "Jakarta Selatan"},
    {"name": "Aspen Jl. Fatmawati", "cat": "APARTEMEN/KOS", "lon": 106.7935, "lat": -6.2940, "price": 2_400_000_000, "area": 111, "sale": "jual", "bed": 3, "url": "https://www.brighton.co.id/dijual/apartment/jakarta-selatan/fatmawati", "src": "Brighton", "date": "2026-02-23", "district": "Cilandak", "city": "Jakarta Selatan"},
]


def hav(a, b):
    r = 6371000.0
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, h)))


def load_fc(path):
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text()).get("features") or []


def flatten_line(g):
    t = (g or {}).get("type")
    c = (g or {}).get("coordinates") or []
    if t == "LineString":
        return [c]
    if t == "MultiLineString":
        return c
    return []


def sample_line(coords, step=280):
    if len(coords) < 2:
        return coords[:1]
    out = [coords[0]]
    acc = 0.0
    for a, b in zip(coords, coords[1:]):
        acc += hav(a, b)
        if acc >= step:
            out.append(b)
            acc = 0.0
    out.append(coords[-1])
    return out


def load_networks():
    nets = []
    specs = [
        (PUB / "krl_routes.geojson", "existing", "krl"),
        (PUB / "mrt_routes.geojson", "existing", "mrt"),
        (PUB / "lrt_routes.geojson", "existing", "lrt"),
        (PUB / "transjakarta_routes.geojson", "existing", "transjakarta"),
        (PUB / "masterplan.geojson", "masterplan", "masterplan"),
        (PUB / "cascade_candidates.geojson", "cascade", "cascade"),
    ]
    for path, kind, mode in specs:
        for f in load_fc(path):
            rid = str(f.get("id") or (f.get("properties") or {}).get("id") or (f.get("properties") or {}).get("route_id") or "")
            name = (f.get("properties") or {}).get("name") or rid
            pts = []
            for run in flatten_line(f.get("geometry")):
                pts.extend(sample_line(run, 350))
            if pts:
                nets.append({"id": rid, "name": name, "kind": kind, "mode": mode, "pts": pts})
    stops = []
    for path, kind in [
        (PUB / "krl_stops.geojson", "existing"),
        (PUB / "mrt_stops.geojson", "existing"),
        (PUB / "lrt_stops.geojson", "existing"),
        (PUB / "transjakarta_stops.geojson", "existing"),
        (PUB / "masterplan_stations.geojson", "masterplan"),
        (PUB / "cascade_stops.geojson", "cascade"),
    ]:
        for f in load_fc(path):
            g = f.get("geometry") or {}
            if g.get("type") != "Point":
                continue
            c = g["coordinates"]
            p = f.get("properties") or {}
            stops.append({"kind": kind, "name": p.get("name") or p.get("stop_name") or "", "lon": c[0], "lat": c[1]})
    return nets, stops


def nearest_net(pt, nets, kind):
    best = (9e9, None)
    for n in nets:
        if n["kind"] != kind:
            continue
        d = min(hav(pt, q) for q in n["pts"][::2] or n["pts"])
        if d < best[0]:
            best = (d, n)
    return best


def nearest_stop(pt, stops):
    best = (9e9, None)
    for s in stops:
        d = hav(pt, (s["lon"], s["lat"]))
        if d < best[0]:
            best = (d, s)
    return best


def pid(*parts):
    raw = "|".join(str(p) for p in parts)
    return "P-" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def idr(n):
    if n is None:
        return None
    n = float(n)
    if n >= 1_000_000_000:
        return f"Rp{n/1_000_000_000:.2f} M".replace(".", ",")
    if n >= 1_000_000:
        return f"Rp{n/1_000_000:.0f} jt"
    return f"Rp{n:,.0f}".replace(",", ".")


def rec_base():
    return {
        "source_type": "PUBLIC_LISTING",
        "listing_type": "sale",
        "sale_or_rent": "jual",
        "property_status": "listed",
        "data_timestamp": RETRIEVED,
        "outlier_flag": 0,
    }


def build_records(nets, stops):
    rows = []
    # Specific asking-price listings
    for L in LISTINGS:
        ppm2 = L["price"] / L["area"] if L.get("area") else None
        pt = (L["lon"], L["lat"])
        rows.append(make_row(
            nets, stops,
            name=L["name"], cat=L["cat"], pt=pt, price=L["price"], area_b=L["area"],
            sale="jual", bed=L.get("bed"), url=L["url"], src=L["src"], date=L["date"],
            district=L["district"], city=L["city"],
            label="ASKING PRICE", conf="HIGH", geom="LISTING_COORD",
            note=L.get("note"), ppm2=ppm2, sub="apartemen" if L["cat"].startswith("APA") else None,
        ))
    # Neighborhood estimated market range — 3 categories, jual + kos sewa
    for a in AREAS:
        name, lon, lat, dist, city, apt_m2, land_m2, ruko, kos, url, note = a
        # slight category offsets so symbols don't stack
        apt_pt = (lon + 0.0012, lat)
        ruko_pt = (lon - 0.0011, lat + 0.0008)
        tanah_pt = (lon + 0.0004, lat - 0.0010)
        apt_area = 50.0
        rows.append(make_row(
            nets, stops, name=f"Apartemen/kos {name}", cat="APARTEMEN/KOS", pt=apt_pt,
            price=apt_m2 * apt_area, area_b=apt_area, sale="jual", url=url, src="indeks publik 2026",
            date="2026-06", district=dist, city=city, label="ESTIMATED MARKET RANGE",
            conf="MEDIUM", geom="NEIGHBORHOOD_CENTROID", note=note, ppm2=apt_m2,
            pmin=apt_m2 * 40, pmax=apt_m2 * 75, sub="apartemen",
        ))
        rows.append(make_row(
            nets, stops, name=f"Ruko {name}", cat="RUKO", pt=ruko_pt,
            price=ruko, area_b=120.0, sale="jual", url=url, src="indeks publik 2026",
            date="2026-06", district=dist, city=city, label="ESTIMATED MARKET RANGE",
            conf="MEDIUM", geom="NEIGHBORHOOD_CENTROID", note=note, ppm2=ruko / 120.0,
            pmin=ruko * 0.7, pmax=ruko * 1.4, sub="ruko",
        ))
        rows.append(make_row(
            nets, stops, name=f"Tanah {name}", cat="TANAH", pt=tanah_pt,
            price=land_m2 * 200.0, area_l=200.0, sale="jual", url=url, src="indeks publik 2026",
            date="2026-06", district=dist, city=city, label="ESTIMATED MARKET RANGE",
            conf="MEDIUM", geom="NEIGHBORHOOD_CENTROID", note=note, ppm2=land_m2,
            pmin=land_m2 * 120, pmax=land_m2 * 400, sub="tanah kosong",
        ))
        rows.append(make_row(
            nets, stops, name=f"Kos {name}", cat="APARTEMEN/KOS", pt=(lon - 0.0006, lat - 0.0005),
            price=kos, sale="sewa", url=url, src="indeks publik 2026",
            date="2026-06", district=dist, city=city, label="ESTIMATED MARKET RANGE",
            conf="MEDIUM", geom="NEIGHBORHOOD_CENTROID", note="Sewa bulanan kisaran publik, bukan asking unit tertentu",
            sub="kos", unit="bulan",
        ))
    return rows


def make_row(nets, stops, *, name, cat, pt, price, sale, url, src, date, district, city, label, conf, geom, note=None, area_b=None, area_l=None, bed=None, ppm2=None, pmin=None, pmax=None, sub=None, unit=None):
    dex, nex = nearest_net(pt, nets, "existing")
    dmp, nmp = nearest_net(pt, nets, "masterplan")
    dca, nca = nearest_net(pt, nets, "cascade")
    ds, ns = nearest_stop(pt, stops)
    rel = sorted(
        [
            (dex, "existing", nex),
            (dmp, "masterplan", nmp),
            (dca, "cascade", nca),
        ],
        key=lambda t: t[0],
    )[0]
    rid = pid(name, round(pt[0], 5), round(pt[1], 5), sale)
    return {
        "property_id": rid,
        "source": src,
        "source_url": url,
        "source_type": "PUBLIC_LISTING" if label == "ASKING PRICE" else "PUBLIC_INDEX",
        "category": cat,
        "sub_category": sub,
        "title": name,
        "property_name": name,
        "latitude": round(pt[1], 6),
        "longitude": round(pt[0], 6),
        "address": f"{district}, {city}",
        "district": district,
        "city": city,
        "price": price,
        "price_min": pmin,
        "price_max": pmax,
        "price_unit": unit or ("total" if sale == "jual" else "bulan"),
        "area_land_m2": area_l,
        "area_building_m2": area_b,
        "price_per_m2": ppm2,
        "listing_type": "sale" if sale == "jual" else "rent",
        "sale_or_rent": sale,
        "bedroom": bed,
        "bathroom": None,
        "floor": None,
        "property_status": "listed" if label == "ASKING PRICE" else "index",
        "date_listed": date,
        "date_updated": RETRIEVED,
        "data_timestamp": RETRIEVED,
        "confidence_score": conf,
        "geometry_source": geom,
        "corridor_id": rel[2]["id"] if rel[2] else None,
        "corridor_type": rel[1],
        "distance_to_corridor": round(rel[0], 1),
        "distance_to_station": round(ds, 1),
        "nearest_station": (ns or {}).get("name"),
        "existing_corridor_id": nex["id"] if nex else None,
        "existing_distance_m": round(dex, 1) if nex else None,
        "masterplan_corridor_id": nmp["id"] if nmp else None,
        "masterplan_distance_m": round(dmp, 1) if nmp else None,
        "cascade_corridor_id": nca["id"] if nca else None,
        "cascade_distance_m": round(dca, 1) if nca else None,
        "price_label": label,
        "note": note,
        "cell_id": f"{round(pt[0] / 0.02) * 0.02:.3f}:{round(pt[1] / 0.02) * 0.02:.3f}",
        "outlier_flag": 0,
    }


def classify(rows):
    # Separate jual vs sewa; class from local cell distribution of comparable metric
    groups = defaultdict(list)
    for r in rows:
        key = (r["sale_or_rent"], r["cell_id"])
        metric = r.get("price_per_m2") if r["sale_or_rent"] == "jual" and r.get("price_per_m2") else r.get("price")
        r["_metric"] = metric
        groups[key].append(r)
    for key, items in groups.items():
        vals = sorted(x["_metric"] for x in items if x["_metric"])
        if len(vals) < 4:
            # widen: same sale type city-wide later
            continue
        lo, hi = vals[max(0, len(vals) // 3 - 1)], vals[min(len(vals) - 1, (len(vals) * 2) // 3)]
        for r in items:
            m = r["_metric"]
            if m is None:
                r["price_class"] = None
            elif m <= lo:
                r["price_class"] = "MURAH"
            elif m >= hi:
                r["price_class"] = "MAHAL"
            else:
                r["price_class"] = "SEDANG"
            med = vals[len(vals) // 2]
            r["local_price_index"] = round(m / med, 3) if med else None
    # fallback city-wide per sale type
    by_sale = defaultdict(list)
    for r in rows:
        by_sale[r["sale_or_rent"]].append(r)
    for sale, items in by_sale.items():
        vals = sorted(x["_metric"] for x in items if x["_metric"])
        if not vals:
            continue
        lo, hi = vals[max(0, len(vals) // 3 - 1)], vals[min(len(vals) - 1, (len(vals) * 2) // 3)]
        med = vals[len(vals) // 2]
        for r in items:
            if r.get("price_class"):
                continue
            m = r["_metric"]
            if m is None:
                r["price_class"] = None
                continue
            if m <= lo:
                r["price_class"] = "MURAH"
            elif m >= hi:
                r["price_class"] = "MAHAL"
            else:
                r["price_class"] = "SEDANG"
            r["local_price_index"] = round(m / med, 3) if med else None
    # outliers
    for sale, items in by_sale.items():
        vals = [x["_metric"] for x in items if x["_metric"]]
        if len(vals) < 8:
            continue
        med = sorted(vals)[len(vals) // 2]
        for r in items:
            if r["_metric"] and med and (r["_metric"] > 4 * med or r["_metric"] < med / 8):
                r["outlier_flag"] = 1
    for r in rows:
        r.pop("_metric", None)
    return rows


def zones(rows):
    cells = defaultdict(list)
    for r in rows:
        if r["sale_or_rent"] != "jual" or r["outlier_flag"] or r["confidence_score"] == "LOW":
            continue
        if not r.get("price_per_m2"):
            continue
        cells[r["cell_id"]].append(r)
    feats = []
    for cid, items in cells.items():
        if len(items) < 4:
            lon0, lat0 = (float(x) for x in cid.split(":"))
            feats.append({
                "type": "Feature",
                "properties": {
                    "cell_id": cid, "n": len(items), "status": "INSUFFICIENT DATA",
                    "price_class": None, "median_price_per_m2": None,
                },
                "geometry": {"type": "Polygon", "coordinates": [cell_ring(lon0, lat0, 0.01)]},
            })
            continue
        vals = sorted(x["price_per_m2"] for x in items)
        med = vals[len(vals) // 2]
        cls = Counterish(items)
        lon0, lat0 = (float(x) for x in cid.split(":"))
        feats.append({
            "type": "Feature",
            "properties": {
                "cell_id": cid,
                "n": len(items),
                "status": "OK",
                "median_price_per_m2": med,
                "median_price": sorted(x["price"] for x in items)[len(items) // 2],
                "price_class": cls,
                "murah_pct": round(100 * sum(1 for x in items if x["price_class"] == "MURAH") / len(items), 1),
                "sedang_pct": round(100 * sum(1 for x in items if x["price_class"] == "SEDANG") / len(items), 1),
                "mahal_pct": round(100 * sum(1 for x in items if x["price_class"] == "MAHAL") / len(items), 1),
            },
            "geometry": {"type": "Polygon", "coordinates": [cell_ring(lon0, lat0, 0.01)]},
        })
    return feats


def Counterish(items):
    c = {"MURAH": 0, "SEDANG": 0, "MAHAL": 0}
    for x in items:
        if x.get("price_class") in c:
            c[x["price_class"]] += 1
    return max(c, key=c.get)


def cell_ring(lon, lat, half):
    return [
        [lon - half, lat - half],
        [lon + half, lat - half],
        [lon + half, lat + half],
        [lon - half, lat + half],
        [lon - half, lat - half],
    ]


def summaries(rows, nets):
    out = []
    for n in nets:
        buf = 500 if n["mode"] in ("mrt", "lrt") else 600 if n["mode"] == "krl" else 400
        inside = []
        for r in rows:
            pt = (r["longitude"], r["latitude"])
            d = min(hav(pt, q) for q in n["pts"][::3] or n["pts"])
            if d <= buf:
                inside.append((r, d))
        jual = [r for r, _ in inside if r["sale_or_rent"] == "jual"]
        if not jual and not inside:
            continue
        def med(vals):
            vals = sorted(v for v in vals if v is not None)
            return vals[len(vals) // 2] if vals else None
        mix = defaultdict(int)
        cls = defaultdict(int)
        for r, _ in inside:
            mix[r["category"]] += 1
            if r.get("price_class"):
                cls[r["price_class"]] += 1
        tot = max(1, sum(cls.values()))
        insight = insight_text(n, jual, mix, cls, buf)
        out.append({
            "corridor_id": n["id"],
            "corridor_name": n["name"],
            "corridor_type": n["kind"],
            "mode": n["mode"],
            "buffer_m": buf,
            "property_count": len(inside),
            "tanah": mix["TANAH"],
            "ruko": mix["RUKO"],
            "apartemen_kos": mix["APARTEMEN/KOS"],
            "median_price": med([r["price"] for r in jual]),
            "median_price_per_m2": med([r.get("price_per_m2") for r in jual]),
            "murah_pct": round(100 * cls["MURAH"] / tot, 1),
            "sedang_pct": round(100 * cls["SEDANG"] / tot, 1),
            "mahal_pct": round(100 * cls["MAHAL"] / tot, 1),
            "nearest_m": round(min((d for _, d in inside), default=0), 1),
            "max_price": max((r["price"] for r in jual), default=None),
            "min_price": min((r["price"] for r in jual), default=None),
            "insight": insight,
            "data_sufficient": len(jual) >= 4,
        })
    return out


def insight_text(n, jual, mix, cls, buf):
    if len(jual) < 4:
        return f"Data harga di buffer {buf} m koridor {n['name']} belum mencukupi untuk delineasi."
    tot = max(1, sum(cls.values()))
    dom = max(mix, key=mix.get) if mix else "—"
    price_dom = max(cls, key=cls.get) if cls else "—"
    med = sorted(r.get("price_per_m2") or 0 for r in jual)
    medv = med[len(med) // 2] if med else 0
    return (
        f"Di sekitar {n['name']} ({n['kind']}), kategori dominan {dom.lower()}. "
        f"Kelas harga lokal paling banyak {price_dom.lower()} ({round(100*cls[price_dom]/tot)}%). "
        f"Median harga/m² jual {idr(medv)}. "
        f"Ini pola spasial, bukan bukti bahwa transportasi menaikkan harga."
    )


def main():
    print("loading networks (read-only)...")
    nets, stops = load_networks()
    print(f"  corridors={len(nets)} stops={len(stops)}")
    rows = classify(build_records(nets, stops))
    print(f"  properties={len(rows)}")
    feats = []
    for r in rows:
        feats.append({
            "type": "Feature",
            "id": r["property_id"],
            "properties": r,
            "geometry": {"type": "Point", "coordinates": [r["longitude"], r["latitude"]]},
        })
    zf = zones(rows)
    sums = summaries(rows, nets)
    insights = [
        {
            "corridor_id": s["corridor_id"],
            "corridor_name": s["corridor_name"],
            "corridor_type": s["corridor_type"],
            "text": s["insight"],
            "median_price": s["median_price"],
            "median_price_per_m2": s["median_price_per_m2"],
            "dominant_category": max(
                (("TANAH", s["tanah"]), ("RUKO", s["ruko"]), ("APARTEMEN/KOS", s["apartemen_kos"])),
                key=lambda t: t[1],
            )[0] if s["property_count"] else None,
            "source": "CASCADE property cache — indeks publik 2026 + listing 99.co/Brighton",
            "updated": RETRIEVED,
        }
        for s in sums
        if s["property_count"]
    ]
    (OUT / "properties.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False))
    (OUT / "price_zones.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": zf}, ensure_ascii=False))
    (OUT / "corridor_summaries.json").write_text(json.dumps(sums, ensure_ascii=False))
    (OUT / "insights.json").write_text(json.dumps(insights, ensure_ascii=False))
    (OUT / "meta.json").write_text(json.dumps({
        "count": len(rows),
        "zones": len(zf),
        "summaries": len(sums),
        "retrieved": RETRIEVED,
        "disclaimer": "Harga asking dari listing publik; kisaran kawasan dari indeks 2026. Bukan nilai transaksi. OSM tidak dipakai sebagai sumber harga.",
        "categories": ["TANAH", "RUKO", "APARTEMEN/KOS"],
        "price_classes": ["MURAH", "SEDANG", "MAHAL"],
        "colors": {"MURAH": "#4FAF86", "SEDANG": "#E5A13A", "MAHAL": "#D62F7F"},
    }, ensure_ascii=False, indent=2))
    print("wrote", OUT, "n=", len(rows), "zones", len(zf), "summaries", len(sums))


if __name__ == "__main__":
    main()
