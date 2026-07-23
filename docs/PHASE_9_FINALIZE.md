# Phase 9 — Finalize & Definition-of-Done Pass

**Status:** Deferred until Phase 6 (billing) lands. Pure polish — no new business logic.

**Original spec:** `specs/SABIL_BACKEND_DJANGO.md` §10 (row "9") and §11 (DoD checklist).

---

## Intent

Once all business phases are built, Phase 9 makes the project look and behave like a production-ready codebase rather than a half-finished sprint. No new features, no new endpoints. Just polish.

---

## Tasks

### 1. OpenAPI schema cleanup
- Run `docker compose exec backend python manage.py spectacular --file /tmp/schema.yml --validate` and resolve every warning (Phase 5 already removed errors; some warnings may remain in Knox/auth views).
- Add operation `tags` to every endpoint so swagger UI groups them: `["auth"]`, `["catalog"]`, `["provider"]`, `["family"]`, `["billing"]`.
- Add `description` to every viewset method via docstrings — spectacular picks them up automatically.
- Add response examples for the 5 most-used endpoints (listings list, inquiry create, subscription create, etc.) via `OpenApiExample`.
- Add `SECURITY` info in `SPECTACULAR_SETTINGS` so swagger UI's "Authorize" dialog accepts Bearer tokens.
- Update `SPECTACULAR_SETTINGS["VERSION"]` to match `pyproject.toml::version` (read it dynamically via `importlib.metadata`).

### 2. Production settings stub
Currently there's no `conf/prod.py` or settings split. Spec §3 expected it.

Options:
- **Single `conf/settings.py` with env-driven branching** (current pattern). Add a `conf/prod.py` that re-exports `settings.py` and asserts `DEBUG=False`, `SECRET_KEY` is set, `ALLOWED_HOSTS` is populated. Document `DJANGO_SETTINGS_MODULE=conf.prod` for production.
- **Split into `conf/base.py` + `conf/dev.py` + `conf/prod.py`** (what the spec literally says). Bigger refactor; only do if env-branching gets unwieldy.

Recommended: the env-driven branching has scaled to 4 apps fine. Add a thin `conf/prod.py` wrapper that imports `settings.py` and adds hard assertions. Don't split unless production usage justifies it.

### 3. README rewrite
The current `README.md` is the wilfredinni starter template README. Replace with Sabil-specific content:
- Project intent (one paragraph)
- Quickstart (`make up`, `make seed`, `make superuser`, `make test`)
- Architecture overview (apps, auth model, role system, billing model)
- Link to OpenAPI docs (`/api/schema/swagger-ui/`)
- Link to `specs/SABIL_BACKEND_DJANGO.md` for the full spec
- Link to `docs/PHASE_6_BILLING.md` if Phase 6 is still deferred
- Deployment notes (Docker, env vars, the `DJANGO_SETTINGS_MODULE=conf.prod` switch)

Use `oh-my-claudecode:readme-generator` skill or just write it manually — README is 1-2 pages.

### 4. Update `AGENTS.md`
Currently describes the starter template's apps (`apps/users/`, `apps/core/`). Update to list all Sabil apps:
- `apps.users/` — custom user + roles + auth
- `apps.catalog/` — listing directory
- `apps.providers/` — provider self-service
- `apps.inquiries/` — tutoring inquiries
- `apps.subscriptions/` — masterclass enrollments
- `apps.suggestions/` — family→admin sourcing
- `apps.reviews/` — Phase 7
- `apps.billing/` — Phase 6 (when added)

Document conventions: TextChoices for enums, services.py for business logic, JSON fields for lists, UUID PKs for public-facing models, BigAutoField for User.

### 5. Data migration: ensure all "always present" seed rows exist
- `CommissionRule` with `is_active=True` (Phase 6 data migration — track here so it lands)
- At least one `SubscriptionPlan` (Phase 6 data migration)
- Optional: seed an admin user via a management command for fresh dev installs

### 6. Spec §11 DoD checklist
Walk through every line of spec §11 and verify:
- [ ] Custom User in place; JWT/Knox register/login/refresh/me work with correct roles
- [ ] Public `/listings/` supports category, search, price, age, distance-sort; ACTIVE only
- [ ] `seed_catalog` reproduces the 24 listings exactly
- [ ] Django admin lists/filters every model + approve/reject + verify_providers
- [ ] Provider can manage only their own listings; new listings require admin approval
- [ ] Family→inquiry→provider accept creates a PENDING `CommissionRecord` (Phase 6)
- [ ] Provider earnings endpoint reports accepted/pending/paid (Phase 6)
- [ ] Reviews update denormalized rating/review_count (Phase 7)
- [ ] `/api/schema/` and `/api/docs/` reflect §9 contract
- [ ] `manage.py check` clean; tests green

For any line that fails, file a follow-up task. Do not mark DoD passed if anything fails.

### 7. CI / pre-commit
If the project doesn't yet have CI:
- Add `.github/workflows/test.yml` running `make test` on push/PR
- Add `pre-commit` config running `ruff check` + `ruff format --check` + `mypy`
- Document in README

(If CI already exists via the starter template, just verify it still passes.)

### 8. Logging review
- Verify `LOGGING` config in `conf/settings.py` still works for all new apps
- Confirm `RequestIDMiddleware` correlation works end-to-end
- Spot-check that `logger.info(...)` calls in services emit structured JSON in Docker logs

### 9. Performance sanity check
- `EXPLAIN ANALYZE` the listings query with all filters + distance sort. If > 50ms on 24-row dataset, investigate (probably fine).
- Index sanity: `Listing.status`, `Listing.category`, `Listing.is_featured` should all have `db_index=True`. Verify.
- N+1 check: provider listing endpoint should use `select_related("owner")`; inquiry/subscription serializers should use `select_related("listing", "family", "provider")`.

### 10. Security review
- Confirm `IsFamily`, `IsProvider`, `IsListingOwner` are applied everywhere they should be
- Confirm no endpoint leaks `password`, `admin_notes`, `email` of other users
- Run `oh-my-claudecode:security-reviewer` skill against the diff from Phase 1 to current
- Check `DEBUG=False` strips error details in responses
- Confirm CORS_ALLOW_ALL_ORIGINS is False in prod settings; CORS_ALLOWED_ORIGINS is populated

---

## NOT in scope for Phase 9

- New features
- Refactors that change behavior
- Removing technical debt that isn't blocking DoD
- Test coverage increases beyond what DoD requires
- Wagtail blog (Phase 8, explicitly deferred in spec)

---

## Estimated effort

~2-4 hours with the django-developer agent. Most of the work is OpenAPI cleanup and README rewriting; the actual code changes are small.
