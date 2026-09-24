# Art Marketplace (เว็บขายรูปวาด)

Flask web app for the group project brief: student art marketplace with
login/roles, full CRUD + validation, search/filter/sort/pagination, an
admin dashboard, an audit log, and Vercel deployment.

## Feature checklist (against the brief)

**บังคับ (required for every project)**
- [x] Register/login, role-based access: `admin`, `staff`, `customer` (`models.py: User.role`)
- [x] Full CRUD on artworks with input validation (`routes/artist.py`, `forms.py`)
- [x] Search, filter (category), sort (price/date), pagination on the gallery (`routes/gallery.py`)
- [x] Dashboard/report page (`/admin/dashboard`)
- [x] Audit log for edits to key data (`models.py: AuditLog`, written on every create/update/delete/status change)
- [x] Deployable to Vercel (`vercel.json`, `api/index.py`)

**ขั้นต่ำ (Art Marketplace minimum)**
- [x] Gallery filtered by category/artist/price (search + category filter + price sort)
- [x] Artwork detail page (image, size, technique, price, sold/available)
- [x] Artist profile + artwork upload
- [x] Cart + ordering
- [x] Slip upload / PromptPay QR + admin confirmation
- [x] Order status tracking (awaiting_payment → paid → shipped → completed)
- [x] Admin approves artworks before they go public

**เสริม (extras) — implemented**
- [x] Automatic watermark on preview images (`utils.py: make_watermarked_preview`, via Pillow)
- [x] Revenue split per artist + per-artist sales report (`ArtistProfile.commission_rate`, admin dashboard)
- [x] "Similar artworks" (same category) on the artwork detail page

**เสริม — not implemented (left as clear extension points, to keep this buildable in the time you have)**
- Full-resolution digital file gated behind purchase — you have the pieces
  (`Artwork.image_filename` is the original, `preview_filename` is the
  watermarked one); add a `/artwork/<id>/download` route that checks the
  buyer owns a `completed` order containing that artwork before serving
  `image_filename`.
- Custom commission requests (a form + a `CommissionRequest` model would
  follow the same pattern as `Order`).
- Reviews / likes / follow-artist (a `Review` model + a few routes).
- Smarter "similar artwork" via tags or image embeddings — currently just
  same-category.

## Project structure

```
app.py              Flask app factory + local dev entrypoint
config.py           Settings (reads DATABASE_URL, SECRET_KEY from env)
extensions.py       db / login_manager instances
models.py           User, ArtistProfile, Category, Artwork, Order, OrderItem, AuditLog
forms.py            WTForms (validation)
decorators.py       role_required(), artist_required()
utils.py            file upload + watermarking helpers
seed.py             demo data (accounts + categories)
routes/             auth, gallery, artist, cart, orders, admin blueprints
templates/          Jinja2 + Bootstrap 5 templates
api/index.py        Vercel serverless entrypoint (imports the same app)
vercel.json         Vercel build/route config
```

## Run it in GitHub Codespaces

```bash
pip install -r requirements.txt
export SECRET_KEY="change-me"
flask --app app init-db      # creates app.db (SQLite) and tables
flask --app app seed-db      # optional: demo accounts + categories
flask --app app run --debug --host 0.0.0.0 --port 5000
```

Codespaces will prompt to forward port 5000 — open it in the browser tab
it offers (or the "Ports" panel). Demo logins after `seed-db` (password
for all: `password123`):

| username | role     |
|----------|----------|
| admin    | admin    |
| staff1   | staff    |
| artist1  | customer + artist profile |
| buyer1   | customer |

Log in as `admin`, go to **จัดการหมวดหมู่** to see the seeded categories,
then log in as `artist1` to upload an artwork — it needs admin/staff
approval (**อนุมัติผลงาน**) before it shows up in the public gallery.

## Deploying to Vercel

Vercel's Python runtime is **serverless**: the filesystem is read-only
except `/tmp`, and `/tmp` is wiped between cold starts / deployments.
That means the SQLite fallback and local file uploads only work for a
quick demo — **for anything you need to keep, wire up two things**:

1. **A real database.** Create a free Postgres instance (Vercel Postgres,
   [Neon](https://neon.tech), or Supabase all work) and set its connection
   string as the `DATABASE_URL` environment variable in your Vercel
   project settings. The app already handles `postgres://` → `postgresql://`
   normalization in `config.py`.
2. **Persistent file storage** for artwork images and payment slips —
   e.g. an S3-compatible bucket or Cloudinary. `utils.py: save_upload()`
   is the one place that writes files; point it at your storage provider's
   SDK instead of the local filesystem when you're ready to go past a demo.
   Until then, uploads will "work" during a session but can vanish on the
   next cold start.

Steps:

```bash
npm i -g vercel        # if you don't have the CLI yet
vercel login
vercel                 # first deploy, follow the prompts
vercel env add SECRET_KEY
vercel env add DATABASE_URL     # your Postgres connection string
vercel --prod
```

After the first deploy, initialize tables against your real database once
(run `flask --app app init-db` locally with `DATABASE_URL` pointed at the
same Postgres instance, or add a one-off script) — the app also tries
`db.create_all()` on cold start as a convenience, but a proper migration
step is safer once you have real data.

## Notes on the audit log

Every create/update/delete on artworks, orders (including status changes),
categories, and user roles writes a row to `audit_logs` via
`AuditLog.record(...)`. Admins can review it at `/admin/logs`.
