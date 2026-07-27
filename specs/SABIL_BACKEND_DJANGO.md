# Sabil Platform — Backend Implementation Instruction (Django + DRF)

> **For use with Claude Code (CLI) as an agentic build guide.**
> Save at the backend repo root. Put **Agent Operating Rules** into `CLAUDE.md`. Build **one phase at a time**, verify, then continue.
> Companion file: `SABIL_PROVIDER_FRONTEND.md` consumes the API contract in Section 9. Keep the two in sync.

---

## 0. Summary

The backend serves both products (Sabilbooks + Sabil Life) through one Django project. **This instruction scopes the slice needed now:** the Sabil Life directory API, accounts/auth with roles, the provider (tutor / masterclass) self-service surface, the student-inquiry → match flow, and the commission engine that the business runs on.

**Why Django + DRF (not FastAPI):** this product is content- and role-heavy. Django gives us a production-grade admin panel for listing moderation, a complete auth/permissions system, and an ORM with migrations out of the box — weeks of saved work versus assembling the same on FastAPI. The frontends (Vue web, Flutter mobile) are fully decoupled and consume DRF as a pure JSON API.

| Attribute | Value |
|-----------|-------|
| Language / framework | Python 3.12, Django 5.x, Django REST Framework |
| Database | PostgreSQL 16 |
| Auth | `djangorestframework-simplejwt` (JWT access + refresh) |
| Admin / moderation | Django admin (built-in) |
| Blog / CMS | Wagtail — **deferred**, stubbed only (Phase 8) |
| API docs | `drf-spectacular` (OpenAPI 3) |
| Async jobs | Celery + Redis — **deferred** to a later phase (email, payment webhooks) |
| Image handling | Pillow; store URLs now, S3 later |
| CORS | `django-cors-headers` for Vue + Flutter origins |
| Currency in seed data | QAR |

---

## 1. Agent Operating Rules (put in CLAUDE.md)

1. **One Django app per bounded context.** Do not pile models into a single app.
2. **Custom User model from commit one.** Never use the default `auth.User`; swapping later is painful. Set `AUTH_USER_MODEL` before the first migration.
3. **Thin views, fat serializers/services.** Business rules (commission calc, inquiry state transitions) live in `services.py`, not in views.
4. **Every model registered in Django admin** with sensible `list_display`, `list_filter`, `search_fields`, and moderation actions where relevant.
5. **Seed data must mirror the Flutter mock set** (same ~24 Doha listings) so the mobile team can integration-test against identical content.
6. **Permissions are explicit.** Public read endpoints are open; everything that writes provider/inquiry/commission data is role-gated.
7. **No business logic in migrations.** Migrations are schema only.
8. **After every phase:** `python manage.py makemigrations && migrate`, `python manage.py check`, run `pytest` (or `manage.py test`), and confirm `runserver` boots. Report results before continuing.
9. **Keep the API contract (Section 9) authoritative.** If you change a field name or shape, update Section 9 and flag it so the frontend file can follow.

---

## 2. Dependencies (`requirements.txt`)

```
Django>=5.0,<5.2
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
django-cors-headers>=4.3
drf-spectacular>=0.27
psycopg[binary]>=3.1
Pillow>=10.0
python-decouple>=3.8        # env config
django-filter>=24.1         # query filtering on listings
pytest-django>=4.8          # tests
```
Wagtail, Celery, redis, stripe are added in their own later phases — do **not** install them now.

**Verification:** `pip install -r requirements.txt` succeeds; `django-admin --version` prints 5.x.

---

## 3. Project Layout

```
config/
  settings/
    base.py            # shared settings, INSTALLED_APPS, DRF, JWT, CORS
    dev.py             # sqlite or local postgres, DEBUG=True
    prod.py            # postgres, DEBUG=False (stub for later)
  urls.py              # /api/ router + /admin/ + /api/schema/, /api/docs/
  asgi.py  wsgi.py
apps/
  common/
    models.py          # TimeStampedModel base (created_at, updated_at)
    permissions.py     # IsProvider, IsFamily, IsOwnerOrReadOnly
    pagination.py      # default page size 20
  accounts/
    models.py          # User (custom), Role choices
    serializers.py     # Register, Login(token), User
    views.py           # register, me  (+ simplejwt views in urls)
    urls.py
    admin.py
  catalog/
    models.py          # Category(enum via TextChoices on Listing), Listing
    serializers.py     # ListingList, ListingDetail
    filters.py         # category, q, price_max, age, geo distance, sort
    views.py           # public read-only ViewSet
    services.py        # haversine annotate / distance ordering
    admin.py           # moderation: approve/reject actions
    seed.py            # management command data (mirrors Flutter mock)
  providers/
    models.py          # ProviderProfile
    serializers.py
    views.py           # profile + provider-owned listing CRUD
    permissions.py
    urls.py
    admin.py
  inquiries/
    models.py          # Inquiry (the match/lead) + status machine
    serializers.py
    views.py           # family create/list; provider accept/decline
    services.py        # state transitions -> trigger commission
    urls.py
    admin.py
  billing/
    models.py          # CommissionRecord, CommissionRule
    services.py        # compute_commission(inquiry)
    admin.py
  reviews/
    models.py          # Review
    serializers.py
    views.py
    urls.py
    admin.py
manage.py
```

---

## 4. accounts — Users, Roles, Auth (Phase 1)

### 4.1 Model
Custom `User` (email login, no username). Fields:
```
email (unique, USERNAME_FIELD), password
full_name
role            -> TextChoices: FAMILY, TUTOR, MASTERCLASS, ADMIN  (default FAMILY)
phone (optional)
home_lat, home_lng (nullable; families set this for proximity)
is_verified (bool, default False)   # providers verified by admin
is_active, is_staff, date_joined
```
Use a `UserManager` with `create_user` / `create_superuser`. Set `AUTH_USER_MODEL = "accounts.User"` in `base.py`.

> `TUTOR` and `MASTERCLASS` are the two provider roles. Treat them together as "providers" via a helper `user.is_provider`.

### 4.2 Auth
Use simplejwt. Endpoints (Section 9). Register defaults to `FAMILY`; a provider registers with `role` in `{TUTOR, MASTERCLASS}` and starts `is_verified=False` (cannot publish until an admin verifies). `/api/auth/me/` returns the current user.

**Verification:** Register a family + a tutor via httpie/curl; obtain tokens; `me` returns correct role.

---

## 5. catalog — Directory the Flutter app reads (Phase 2)

### 5.1 Listing model
Mirror the Flutter `Listing`:
```
id (uuid pk)
title
category          -> TextChoices: SCHOOLS, NURSERIES, ACTIVITIES, ENTERTAINMENT, TUTORING, MASTERCLASSES, PARTNERSHIPS
subtitle
neighborhood      # e.g. "West Bay, Doha"
lat, lng
price_from_qar (int, 0 = free/NA)
age_groups (JSON list of strings)
image_urls (JSON list)
description (text)
highlights (JSON list)
rating (decimal 2,1, denormalized from reviews)
review_count (int)
is_featured (bool)
status            -> TextChoices: DRAFT, PENDING, ACTIVE, REJECTED  (public API returns ACTIVE only)
owner (FK accounts.User, null=True)   # null = admin-entered; set = provider-managed
created_at, updated_at
```

### 5.2 Public API
Read-only ViewSet. Filtering via `django-filter` + a geo helper: `category`, `q` (title/subtitle icontains), `price_max`, `age`, `max_distance_km` with `lat`/`lng`, and `sort` in `{distance, rating, price_low}`. Distance computed with haversine in `services.py` (annotate + order); only `ACTIVE` listings are returned. Detail endpoint embeds reviews.

### 5.3 Seed command
`python manage.py seed_catalog` inserts the same ~24 Doha listings as the Flutter mock (4 schools, 3 nurseries, 6 activities, 3 entertainment, 3 tutoring, 3 masterclasses, 2 partners), fictional names, real neighborhoods, `picsum.photos/seed/<id>` images, ~6 featured, all `ACTIVE`.

**Verification:** `GET /api/listings/?sort=distance&lat=25.369&lng=51.551` returns ordered results; `?category=TUTORING` filters correctly.

---

## 6. providers — Self-service surface (Phase 4)

### 6.1 ProviderProfile
```
user (OneToOne accounts.User, role in {TUTOR, MASTERCLASS})
display_name
bio (text)
subjects (JSON list)      # tutors: ["Math","Arabic"]; masterclass: ["Pottery"]
hourly_rate_qar (int, nullable)
availability (text)
is_verified (mirrors user.is_verified)
```

### 6.2 Provider-owned listings
Provider can CRUD listings **they own** only (`owner == request.user`), enforced by `IsOwnerOrReadOnly` + `IsProvider`. A provider's listing `category` is constrained to match their role (tutor → TUTORING, masterclass → MASTERCLASSES). New/edited listings are saved as `PENDING` → an admin approves to `ACTIVE` in Django admin. Unverified providers may create drafts but cannot submit for approval.

**Verification:** Tutor creates a listing → lands in `PENDING`; appears in admin moderation; family directory does not show it until approved.

---

## 7. inquiries + billing — The match & commission engine (Phases 5–6)

This is the revenue core: the platform earns commission when it connects a tutor/provider with a student.

### 7.1 Inquiry (the tracked match/lead)
```
id (uuid)
family (FK User, role FAMILY)
listing (FK Listing)        # the tutor/masterclass listing
provider (FK User)          # denormalized owner of the listing at creation
message (text)
status   -> NEW, CONTACTED, ACCEPTED, DECLINED, COMPLETED
contact_revealed (bool, default False)
commission (FK billing.CommissionRecord, null=True)
created_at, updated_at
```
- **Family creates** an inquiry from a listing (auth required — this is the just-in-time auth trigger on the client).
- **Provider acts**: `accept` or `decline`. On **accept**, run `inquiries.services.accept_inquiry()` which: sets status `ACCEPTED`, reveals contact, and calls `billing.services.compute_commission(inquiry)` to create a `CommissionRecord` against the provider.

### 7.2 billing
```
CommissionRule:  rule_type (FLAT | PERCENT), amount_or_pct, active
CommissionRecord: inquiry (OneToOne), provider (FK User), amount_qar (decimal),
                  rule_applied, status (PENDING | INVOICED | PAID), created_at
```
`compute_commission(inquiry)` reads the active `CommissionRule` and creates a `PENDING` record. Default seed rule: FLAT 50 QAR per accepted match (owner-adjustable in admin). **Actual charging (Stripe) is out of scope** — model the record; mark `PAID` manually in admin for now.

> Business note: the commission is billed to the **provider** (they pay to receive a student), mirroring the contact-reveal model in Sabilbooks. The family is never charged in this flow.

**Verification:** Family inquiry → provider accepts → a `PENDING` CommissionRecord exists with the seeded rule amount; provider earnings endpoint reflects it.

---

## 8. reviews (Phase 7) & blog (Phase 8, deferred)

- **reviews:** `Review(listing, author, rating 1–5, text, created_at)`. Creating a review recomputes the listing's denormalized `rating`/`review_count` (in a service). Auth required to post.
- **blog:** Install Wagtail in its own phase; create a single `BlogPage` model for "A Perfect Read…". Do not start until inquiries/billing are done and approved.

---

## 9. API Contract (authoritative — frontend depends on this)

Base: `/api/`. Auth: `Authorization: Bearer <access>`.

**Auth**
```
POST /auth/register/   {email, password, full_name, role?}        -> {user, access, refresh}
POST /auth/login/      {email, password}                          -> {user, access, refresh}
POST /auth/refresh/    {refresh}                                   -> {access}
POST /auth/logout/     {refresh}                                   -> 204
GET  /auth/me/                                                     -> {user}
```
`user` = `{id, email, full_name, role, is_verified, home_lat, home_lng}`

**Catalog (public)**
```
GET /listings/?category=&q=&price_max=&age=&max_distance_km=&lat=&lng=&sort=&page=
    -> {count, next, previous, results: [ListingCard]}
GET /listings/{id}/   -> ListingDetail (with reviews[])
GET /categories/      -> [{key, count}]
```
`ListingCard` = `{id, title, category, subtitle, neighborhood, lat, lng, rating, review_count, price_from_qar, image_urls, age_groups, is_featured, distance_km}`
`ListingDetail` = ListingCard + `{description, highlights, owner_id, reviews}`

**Provider (role TUTOR/MASTERCLASS)**
```
GET   /provider/profile/                 PATCH /provider/profile/
GET   /provider/listings/   POST /provider/listings/
GET   /provider/listings/{id}/  PATCH … DELETE …
GET   /provider/inquiries/
POST  /provider/inquiries/{id}/accept/    POST /provider/inquiries/{id}/decline/
GET   /provider/earnings/    -> {accepted_count, pending_qar, paid_qar, records:[…]}
```

**Family (role FAMILY)**
```
POST /inquiries/        {listing_id, message}   -> Inquiry
GET  /inquiries/                                 -> family's own inquiries
POST /listings/{id}/reviews/   {rating, text}    -> Review
```

`Inquiry` = `{id, listing_id, provider_id, status, message, contact_revealed, created_at}` (contact details only present when `contact_revealed`).

---

## 10. Phase Plan

| Phase | Deliverable | Verify |
|-------|-------------|--------|
| 0 | Project, settings split, DRF + JWT + CORS + spectacular wired, `common` base | `manage.py check`, `runserver` boots, `/api/docs/` loads |
| 1 | accounts: custom User, roles, register/login/me, admin | register family+tutor, tokens work |
| 2 | catalog: Listing, public read API, filters + distance sort | filtered/sorted GET works |
| 3 | Django admin polish + `seed_catalog` (mirrors Flutter mock) | 24 listings via admin + API |
| 4 | providers: profile + owner-scoped listing CRUD, PENDING→ADMIN approve | tutor listing lands PENDING |
| 5 | inquiries: family create, provider accept/decline, state machine | full inquiry lifecycle |
| 6 | billing: CommissionRule + compute on accept + earnings endpoint | commission record on accept |
| 7 | reviews + rating recompute | posting review updates listing rating |
| 8 | (deferred) Wagtail blog stub | single blog page renders |
| 9 | OpenAPI finalize, seed a CommissionRule, DoD pass | schema matches Section 9 |

Per phase: `makemigrations` → `migrate` → `manage.py check` → tests → `runserver`, then report.

---

## 11. Definition of Done

- [ ] Custom User in place; JWT register/login/refresh/me all work with correct roles.
- [ ] Public `/listings/` supports category, search, price, age, distance-sort; returns only ACTIVE.
- [ ] `seed_catalog` reproduces the Flutter mock set exactly (same 24, same neighborhoods).
- [ ] Django admin lists/filters every model and can approve/reject listings and verify providers.
- [ ] Provider can manage only their own listings; new listings require admin approval.
- [ ] Family→inquiry→provider accept creates a PENDING CommissionRecord using the active rule.
- [ ] Provider earnings endpoint reports accepted count + pending/paid QAR.
- [ ] Reviews update denormalized rating/review_count.
- [ ] `/api/schema/` and `/api/docs/` reflect Section 9 contract.
- [ ] `manage.py check` clean; tests green.

---

## 12. Non-Goals (do not build now)

- No real payment/charging (Stripe) — commission records only; mark paid in admin.
- No Celery/async, no email sending, no push notifications.
- No Sabilbooks marketplace endpoints (separate later instruction).
- No production deploy config beyond a `prod.py` stub.
- No social login (email/password + JWT only for now).
