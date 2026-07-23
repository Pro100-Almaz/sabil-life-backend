# Phase 6 — Billing, Commission, and Contact-Reveal Gating

**Status:** Deferred. MVP ships without payment logic. This document captures the design context so Phase 6 can be picked up cold by any developer.

**Original spec:** `specs/SABIL_BACKEND_DJANGO.md` §7.2.

---

## Why this is deferred

Phase 6 has the most product-design weight in the whole build:
- It introduces real money flows.
- It contradicts itself between the spec's per-accept commission model and the product owner's "subscription tier" addition.
- It requires picking a payment processor (Stripe, QPay, manual bank transfer) — not a code decision.
- It introduces recurring billing — a permanent ops responsibility.

Rushing this would lock in a revenue model before talking to providers about what they'll actually pay for. We're shipping the MVP without the gate and revisiting once the product has live providers.

---

## The intent

When a family inquires on a tutor's listing and the tutor accepts, the **family's contact info** (`full_name`, `phone`, `email`) is currently hidden in the provider's response — every field is `null`. Phase 6's job is to decide *when* those fields flip from null to real values.

That decision = "how does the platform earn money?"

---

## The A vs B decision (still owed)

| | **Path A — Subscription replaces per-accept** | **Path B — Subscription layers on top** |
|---|---|---|
| Free provider | Can accept inquiries, but contact NEVER reveals | Pays N QAR per accept to unlock contact |
| Paid provider | Unlimited reveals; subscription is the only cost | Unlimited reveals; subscription covers per-accept |
| Revenue model | Pure recurring (monthly) | Hybrid: per-accept OR subscription |
| Spec alignment | Contradicts §7.2 (drops `CommissionRecord` entirely) | Preserves §7.2 + adds tier on top |
| Implementation | Drops the per-accept billing path | Two billing flows in parallel |
| Onboarding friction | High — provider gets zero value until they subscribe | Low — first lead can be paid out-of-pocket, subscription is the upgrade |

**Recommended:** **Path B.** It's spec-compatible, lets new providers try the platform with one inquiry before committing to a subscription, and the subscription becomes the upgrade path once they're getting consistent leads. Path A is cleaner code but creates a chicken-and-egg problem for cold-start providers.

This document assumes Path B in the data model. If you switch to A, remove `CommissionRule` + `CommissionRecord` and have the gate check only `ProviderSubscription`.

---

## Free-trial mode (use this until Phase 6 ships)

Before Phase 6 is built, the funnel ends at `ACCEPTED` with `contact_revealed=False` permanently — providers see leads but never get contact details. To unblock real usage during MVP:

Add to `conf/settings.py`:
```python
# Phase 6 not yet built. When False, contact_revealed flips to True automatically
# on inquiry accept (everything is effectively a free trial). Set to True once
# billing is live to enforce the gate.
BILLING_GATE_ENABLED = env.bool("BILLING_GATE_ENABLED", default=False)
```

Add to `apps/inquiries/services.py::transition()`, right after the `inquiry.save()` line:
```python
from django.conf import settings

if action == InquiryStatus.ACCEPTED and not settings.BILLING_GATE_ENABLED:
    inquiry.contact_revealed = True
    inquiry.save(update_fields=["contact_revealed", "updated_at"])
```

Phase 6 will replace this with a real `billing.services.on_inquiry_accepted(inquiry)` call that decides reveal based on subscription/commission state, and the `BILLING_GATE_ENABLED=True` switch enforces it.

---

## Data model (Path B)

### `apps/billing/models.py`

#### `CommissionRule`
The active rule defines how much is owed per accepted inquiry.
```python
class CommissionRuleType(models.TextChoices):
    FLAT = "FLAT"
    PERCENT = "PERCENT"

class CommissionRule(TimeStampedModel):
    rule_type     = CharField(choices=CommissionRuleType.choices, max_length=16)
    amount_or_pct = DecimalField(max_digits=10, decimal_places=2)
    # FLAT: QAR amount. PERCENT: 0-100, applied to listing.price_from_qar at accept time.
    is_active     = BooleanField(default=False)
    notes         = TextField(blank=True, default="")

    class Meta:
        constraints = [
            UniqueConstraint(fields=["is_active"], condition=Q(is_active=True),
                             name="unique_active_commission_rule"),
        ]
```
Only one rule can be `is_active=True` at a time (Postgres partial unique index).

Seed an initial rule via a data migration: `FLAT 50 QAR, is_active=True`.

#### `CommissionRecord`
One row per accepted inquiry.
```python
class CommissionStatus(models.TextChoices):
    PENDING   = "PENDING"      # waiting for provider to pay
    INVOICED  = "INVOICED"     # admin has sent an invoice
    PAID      = "PAID"         # paid out-of-band, contact_revealed flips
    COVERED   = "COVERED"      # provider had active subscription; no payment required, contact_revealed flips
    WAIVED    = "WAIVED"       # admin manually waived (e.g. dispute resolution)

class CommissionRecord(TimeStampedModel):
    inquiry        = OneToOneField("inquiries.Inquiry", on_delete=PROTECT,
                                   related_name="commission")
    provider       = ForeignKey(AUTH_USER_MODEL, on_delete=PROTECT)
    amount_qar     = DecimalField(max_digits=10, decimal_places=2)
    rule_applied   = ForeignKey(CommissionRule, on_delete=PROTECT)
    status         = CharField(choices=CommissionStatus.choices, default=PENDING,
                               max_length=16, db_index=True)
    paid_at        = DateTimeField(null=True, blank=True)
```

#### `SubscriptionPlan`
Admin-curated list of plans.
```python
class SubscriptionPlan(TimeStampedModel):
    name           = CharField(max_length=64)  # "Basic", "Pro"
    price_qar      = PositiveIntegerField()    # 200 = 200 QAR/period
    duration_days  = PositiveIntegerField()    # 30 = monthly
    is_active      = BooleanField(default=True)  # admin can retire plans
    description    = TextField(blank=True, default="")
```

#### `ProviderSubscription`
The actual subscription on a provider.
```python
class SubscriptionStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT"  # provider clicked subscribe, awaiting admin confirm
    ACTIVE          = "ACTIVE"
    EXPIRED         = "EXPIRED"
    CANCELLED       = "CANCELLED"

class ProviderSubscription(TimeStampedModel):
    provider   = ForeignKey(AUTH_USER_MODEL, on_delete=PROTECT,
                            related_name="subscriptions_received")
    plan       = ForeignKey(SubscriptionPlan, on_delete=PROTECT)
    starts_at  = DateTimeField()
    ends_at    = DateTimeField()
    status     = CharField(choices=SubscriptionStatus.choices, max_length=20, db_index=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["provider"], condition=Q(status="ACTIVE"),
                             name="unique_active_subscription_per_provider"),
        ]
```

### `apps/inquiries/models.py` — add the deferred FK

The Phase 5 `Inquiry` model has a comment `# commission FK added in Phase 6 billing app`. Add the field now via a new migration:
```python
commission = OneToOneField("billing.CommissionRecord", null=True, blank=True,
                           on_delete=SET_NULL, related_name="+")
```
(The `OneToOneField` mirrors the `CommissionRecord.inquiry` side; either side works as the canonical accessor.)

---

## The hooks Phase 5 left waiting

These are the exact integration points. Search for "Phase 6" in the codebase to find them all.

1. **`apps/inquiries/services.py::transition()`** — currently just updates status. Phase 6 inserts (after save, when transitioning to ACCEPTED):
   ```python
   from apps.billing.services import on_inquiry_accepted
   if action == InquiryStatus.ACCEPTED:
       on_inquiry_accepted(inquiry)
   ```

2. **`apps/inquiries/serializers.py::ProviderInquirySerializer`** — currently always nulls the family contact block. Change the conditional from `None` to:
   ```python
   def get_family(self, obj):
       base = {"id": str(obj.family.id), "full_name": None, "phone": None, "email": None}
       if obj.contact_revealed:
           base.update({
               "full_name": obj.family.full_name,
               "phone": obj.family.phone,
               "email": obj.family.email,
           })
       return base
   ```

3. **`apps/inquiries/models.py::Inquiry`** — the `commission` FK referenced above needs a migration.

4. **`conf/settings.py`** — `BILLING_GATE_ENABLED` setting (added during MVP free-trial mode). Phase 6 makes this default `True` and ensures the production config sets it.

5. **`/api/v1/provider/earnings/`** — endpoint does not exist yet. Section "Endpoints" below.

---

## The service layer

### `apps/billing/services.py`

```python
def on_inquiry_accepted(inquiry: Inquiry) -> CommissionRecord:
    """
    Called from inquiries.services.transition() when an inquiry transitions to ACCEPTED.

    1. Reads the active CommissionRule.
    2. Computes amount (FLAT or PERCENT of listing price).
    3. Creates a CommissionRecord linked to the inquiry.
    4. Checks the provider's subscription:
       - ACTIVE subscription -> mark COVERED + flip inquiry.contact_revealed=True.
       - No active subscription -> mark PENDING. Contact stays hidden.
    """

def on_commission_paid(record: CommissionRecord) -> None:
    """
    Called from an admin action (mark_paid) or a post_save signal on CommissionRecord.

    Sets paid_at=now() and flips inquiry.contact_revealed=True.
    Idempotent: safe to call repeatedly.
    """

def get_active_subscription(provider) -> ProviderSubscription | None:
    """Returns the ACTIVE subscription if any, else None.

    Also lazily transitions ACTIVE -> EXPIRED if ends_at < now().
    """
```

### Signal — auto-flip contact on PAID

In `apps/billing/signals.py`:
```python
@receiver(post_save, sender=CommissionRecord)
def reveal_contact_on_paid(sender, instance, **kwargs):
    if instance.status in (CommissionStatus.PAID, CommissionStatus.COVERED, CommissionStatus.WAIVED):
        on_commission_paid(instance)
```
Wire it up in `apps.billing.apps.BillingConfig.ready()`.

---

## Endpoints

### Provider (auth, role in TUTOR/MASTERCLASS)

```
GET   /api/v1/provider/earnings/
  ->  {
        "accepted_count": int,
        "completed_count": int,
        "pending_qar": Decimal,
        "paid_qar": Decimal,
        "subscription": {
          "plan_name": str | null,
          "status": str,
          "starts_at": datetime | null,
          "ends_at": datetime | null,
          "days_remaining": int | null
        },
        "recent_records": [
          {id, inquiry_id, amount_qar, status, created_at}, ...
        ]
      }

GET   /api/v1/provider/subscription/
  ->  current ProviderSubscription detail (or null)

POST  /api/v1/provider/subscription/activate/
  body: {plan_id}
  ->  creates ProviderSubscription(status=PENDING_PAYMENT)
      admin flips to ACTIVE manually in /admin-panel/ until Stripe/QPay is wired
```

### Admin (Django admin only)

- `CommissionRule` — change form. Bulk action `activate` (atomically flips active flag).
- `CommissionRecord` list — bulk `mark_paid`, `mark_invoiced`, `mark_waived`. Signal handles contact reveal.
- `SubscriptionPlan` — CRUD.
- `ProviderSubscription` list — bulk `activate` (flips PENDING_PAYMENT→ACTIVE + sets starts_at/ends_at), `extend_30_days`, `expire`, `cancel`.

### Public + family

No new endpoints. Families never see commission/subscription data.

---

## Tests Phase 6 must ship

- `CommissionRule` partial-unique constraint (only one active at a time)
- `on_inquiry_accepted`:
  - Free provider → CommissionRecord PENDING, contact hidden
  - Subscribed provider → CommissionRecord COVERED, contact revealed
  - No active rule configured → 500 / clear error (don't silently swallow)
- `mark_paid` admin action flips contact_revealed
- Subscription auto-expiry: ACTIVE row with `ends_at` in the past returns as EXPIRED on next read
- Earnings endpoint shape — both free and paid providers
- Family-side responses never leak billing/subscription data (regression)
- Masterclass subscriptions (Phase 5 family→masterclass enrollment) unaffected — they auto-confirm regardless of provider's billing state
- `BILLING_GATE_ENABLED=False` (free-trial mode) bypasses commission and auto-flips contact_revealed
- `BILLING_GATE_ENABLED=True` enforces the gate

---

## Open questions to resolve before building

1. **A vs B** — pick one. This doc assumes B.
2. **Payment processor** — Stripe, QPay, manual bank transfer, all of the above? Affects what `subscription/activate/` does. MVP can stub with "admin marks paid"; longer-term needs webhook integration.
3. **Per-accept commission amount** — spec suggests FLAT 50 QAR. Should it scale with listing price (PERCENT)? Different rules per category?
4. **Subscription plan prices** — what monthly cost? Multiple tiers (Basic / Pro / Premium)?
5. **Refunds** — if a tutor's inquiry was declined post-accept, or family disputes, does the commission get waived? Implement now or defer?
6. **Currency** — spec says QAR. Multi-currency support deferred?
7. **Tax** — Qatar has 5% VAT on some services. Apply to commission?
8. **Invoicing** — generate PDF invoices on `mark_invoiced`? Email them via Celery (currently deferred)?
9. **Provider self-cancel** — can a provider cancel their own subscription, or must they ask admin?
10. **Grace period on expiry** — when subscription ends, does contact_revealed retroactively flip back to False on past inquiries? Probably no — past reveals are committed. Document.

---

## Payment-processor integration notes

When picking a processor:

- **Stripe** — best DX, mature webhooks, native subscription primitives. Doesn't have a Qatar entity; you'd settle through their US/EU stack. Some Qatari banks decline foreign processors.
- **QPay** — Qatar Central Bank payment gateway. Local settlement. Requires merchant registration in Qatar. Less developer ergonomic.
- **Manual bank transfer** — what the MVP effectively does. Provider sends QAR to a bank account, admin marks PAID. Zero integration cost, manual ops.

For Phase 6 first pass, stay manual. Add a processor adapter in Phase 6.5 once provider volume justifies the integration cost. The data model above is already processor-agnostic: `CommissionRecord.status` and `ProviderSubscription.status` are the source of truth; processor webhooks just update those rows.

When wiring a processor:
1. New `apps/billing/processors/<name>.py` module with a `charge(record)` / `subscribe(provider, plan)` interface.
2. Webhook endpoint at `/api/v1/billing/webhooks/<processor>/` that verifies signature + updates record/subscription status.
3. Update `subscription/activate/` to call `processor.subscribe()` instead of creating PENDING_PAYMENT directly.
4. Celery task for renewal reminders (Celery is already in the template; just doesn't run any tasks yet).

---

## Definition of done (Phase 6)

- [ ] `apps/billing/` app created, registered, migrated
- [ ] `CommissionRule`, `CommissionRecord`, `SubscriptionPlan`, `ProviderSubscription` models + admin
- [ ] `on_inquiry_accepted` wired into `inquiries.services.transition`
- [ ] `commission` FK added to `Inquiry`
- [ ] `ProviderInquirySerializer.get_family` honors `contact_revealed`
- [ ] `BILLING_GATE_ENABLED` setting respected (defaults to `True` in prod, `False` in dev for trial)
- [ ] `GET /provider/earnings/`, `GET /provider/subscription/`, `POST /provider/subscription/activate/` endpoints
- [ ] Admin actions: mark_paid, mark_invoiced, mark_waived, extend_subscription
- [ ] Initial data migration: one FLAT 50 QAR `CommissionRule` with `is_active=True`
- [ ] Initial data migration: one `SubscriptionPlan` (e.g. "Basic", 200 QAR/30 days)
- [ ] Tests covering both free and paid provider paths
- [ ] OpenAPI schema reflects all new endpoints
- [ ] `python manage.py check`, `pytest`, `ruff` all green

---

## Cross-references

- Original spec: `specs/SABIL_BACKEND_DJANGO.md` §7.2
- Phase 5 hooks: search codebase for `Phase 6` comments
- Phase 9 polish: `docs/PHASE_9_FINALIZE.md`
