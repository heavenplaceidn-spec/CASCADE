# CASCADE — Deployment

Salinan dari repo aplikasi.

- Node 22, TanStack Start, bind `0.0.0.0:8080`
- Auth OFF. PGLite locally; Neon `DATABASE_URL` on deploy.
- Never commit `.env`.
- `npm install && npm run db:migrate && npm run dev`
- Official GTFS / masterplan / Property Go are not seeded.
- Backup/PITR is not a product feature.
