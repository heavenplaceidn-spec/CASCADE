# Cara buka source CASCADE dari akun Arckzz

Konektor Grok memakai `heavenplaceidn-spec`. Dari sini **tidak bisa** mengirim undangan kolaborator atau mengubah repo privat menjadi publik.

Dokumen sudah publik:
https://github.com/heavenplaceidn-spec/CASCADE

Source aplikasi masih privat:
https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal

## Undang Arckzz (2 menit)

1. Logout, login sebagai **heavenplaceidn-spec**.
2. Buka langsung:
   - https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal/settings/access
   - https://github.com/heavenplaceidn-spec/cascade-webgis/settings/access
3. **Add people** → ketik `Arckzz` → **Write** atau **Admin** → Add.
4. Login **Arckzz** → https://github.com/notifications → Accept.
5. Clone:

```bash
git clone https://github.com/heavenplaceidn-spec/turbo-umbra-lagoon-crystal.git cascade
cd cascade
npm install
npm run dev
```

## Alternatif

Hubungkan ulang konektor GitHub Grok ke akun **Arckzz**, lalu minta Grok membuat repo CASCADE di akun itu.
