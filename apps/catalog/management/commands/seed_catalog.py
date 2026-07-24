"""
seed_catalog management command — Phase 3.

Idempotency strategy: update_or_create(id=deterministic_uuid, defaults=...).
Chosen over bulk_create(ignore_conflicts=True) because it also updates fields
when the listing data changes between runs (useful during development), while
still being safe to run repeatedly in production.  Each listing is keyed by a
stable slug fed through uuid.uuid5() so the UUID is always the same.
"""

import uuid
import requests

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.catalog.models import Listing, ListingCategory, ListingStatus, ListingImage
from apps.users.enums import UserRole
from apps.users.models import CustomUser

# Fixed namespace — never change this or all deterministic UUIDs will shift.
NAMESPACE = uuid.UUID("11111111-2222-3333-4444-555555555555")

# Seed providers — non-prod accounts that own seeded TUTORING / MASTERCLASSES
# listings so the family inquiry / subscribe flows have a valid provider FK to
# snapshot. These rows are intentionally lookup-by-email; passwords are usable
# in dev (mirrors `apps/core/management/commands/seed.py`).
SEED_TUTOR_EMAIL = "seed-tutor@sabil.local"
SEED_MC_EMAIL = "seed-masterclass@sabil.local"
SEED_PROVIDER_PASSWORD = "testpass123"


def _uid(slug: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, slug)


def _get_or_create_seed_provider(email: str, role: str, label: str) -> CustomUser:
    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            "role": role,
            "is_verified": True,
            "full_name": f"Seed {label}",
            "is_active": True,
        },
    )
    if created:
        user.set_password(SEED_PROVIDER_PASSWORD)
        user.save(update_fields=["password"])
    return user


def _fetch_image(slug: str, index: int) -> ContentFile | None:
    """Best-effort fetch of a placeholder image for a seeded listing.

    Returns a ContentFile ready for default_storage.save(), or None when the
    image can't be fetched (e.g. seeding offline / in CI). Seeding must never
    fail just because the network is unavailable, so callers skip on None.
    """
    url = f"https://picsum.photos/seed/{slug}-{index}/800/600"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return ContentFile(resp.content)
    except requests.RequestException:
        return None

# ---------------------------------------------------------------------------
# Listing data — 24 entries, easy to scan / review
# ---------------------------------------------------------------------------
LISTINGS: list[dict] = [
    # ── SCHOOLS (4) ─────────────────────────────────────────────────────────
    {
        "slug": "schools-doha-international-academy",
        "title": "Doha International Academy",
        "category": ListingCategory.SCHOOLS,
        "subtitle": "British-curriculum school from Foundation to Year 13",
        "neighborhood": "West Bay",
        "lat": 25.3220,
        "lng": 51.5260,
        "price_from_qar": 18000,
        "age_groups": ["6-9", "10-12", "13-17"],
        "description": (
            "A leading British-curriculum school serving West Bay families "
            "with excellent A-Level results and a strong university placement record."
        ),
        "highlights": [
            "Cambridge A-Level & IGCSE programme",
            "Olympic-size swimming pool",
            "400-seat performing arts theatre",
            "Annual Oxford/Cambridge university tour",
        ],
        "rating": Decimal("4.7"),
        "review_count": 112,
        "is_featured": True,
        "image_count": 2,
    },
    {
        "slug": "schools-pearl-american-school",
        "title": "Pearl American School",
        "category": ListingCategory.SCHOOLS,
        "subtitle": "US-curriculum PK–12 at The Pearl",
        "neighborhood": "The Pearl",
        "lat": 25.3710,
        "lng": 51.5510,
        "price_from_qar": 20000,
        "age_groups": ["6-9", "10-12", "13-17"],
        "description": (
            "Full US curriculum with Advanced Placement courses, "
            "nestled in the heart of The Pearl-Qatar community."
        ),
        "highlights": [
            "College Board AP programme (22 subjects)",
            "State-of-the-art robotics lab",
            "IB Diploma pathway available",
        ],
        "rating": Decimal("4.5"),
        "review_count": 87,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "schools-lusail-french-international",
        "title": "Lusail French International School",
        "category": ListingCategory.SCHOOLS,
        "subtitle": "French Baccalaureate & bilingual education, Lusail",
        "neighborhood": "Lusail",
        "lat": 25.4290,
        "lng": 51.5330,
        "price_from_qar": 16500,
        "age_groups": ["6-9", "10-12", "13-17"],
        "description": (
            "Bilingual French-English instruction following the French Ministry "
            "curriculum, located in the new Lusail district."
        ),
        "highlights": [
            "French Baccalaureate certified",
            "Bilingual French/English from Cycle 1",
            "Regular cultural exchange trips to France",
        ],
        "rating": Decimal("4.4"),
        "review_count": 63,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "schools-knowledge-city-academy",
        "title": "Knowledge City Academy",
        "category": ListingCategory.SCHOOLS,
        "subtitle": "STEM-focused international school in Education City",
        "neighborhood": "Education City",
        "lat": 25.3155,
        "lng": 51.4370,
        "price_from_qar": 17000,
        "age_groups": ["6-9", "10-12", "13-17"],
        "description": (
            "Partners with Qatar Foundation to deliver a STEM-intensive curriculum "
            "for grades 1–12, with access to world-class university facilities."
        ),
        "highlights": [
            "Qatar Foundation partnership",
            "Coding & AI electives from Grade 4",
            "FIRST Robotics competition team",
            "University lab access for senior students",
        ],
        "rating": Decimal("4.8"),
        "review_count": 145,
        "is_featured": True,
        "image_count": 3,
    },
    # ── NURSERIES (3) ────────────────────────────────────────────────────────
    {
        "slug": "nurseries-little-pearls-nursery",
        "title": "Little Pearls Nursery",
        "category": ListingCategory.NURSERIES,
        "subtitle": "Montessori-inspired early years, The Pearl",
        "neighborhood": "The Pearl",
        "lat": 25.3695,
        "lng": 51.5495,
        "price_from_qar": 3500,
        "age_groups": ["0-2", "3-5"],
        "description": (
            "Warm Montessori-inspired environment for children aged 3 months to 4 years, "
            "with bilingual Arabic-English staff."
        ),
        "highlights": [
            "Montessori certified educators",
            "Bilingual Arabic/English programme",
            "Sensory play rooms",
        ],
        "rating": Decimal("4.9"),
        "review_count": 78,
        "is_featured": True,
        "image_count": 2,
    },
    {
        "slug": "nurseries-sunshine-early-learning",
        "title": "Sunshine Early Learning Centre",
        "category": ListingCategory.NURSERIES,
        "subtitle": "Play-based nursery for ages 0–4, Al Waab",
        "neighborhood": "Al Waab",
        "lat": 25.2820,
        "lng": 51.4650,
        "price_from_qar": 2800,
        "age_groups": ["0-2", "3-5"],
        "description": (
            "Child-led play-based learning in a purpose-built garden setting "
            "that encourages curiosity and social development."
        ),
        "highlights": [
            "Dedicated sensory garden",
            "EYFS framework",
            "Flexible half-day options",
        ],
        "rating": Decimal("4.6"),
        "review_count": 54,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "nurseries-crescent-moon-nursery",
        "title": "Crescent Moon Nursery",
        "category": ListingCategory.NURSERIES,
        "subtitle": "Islamic-values nursery, Al Sadd",
        "neighborhood": "Al Sadd",
        "lat": 25.2790,
        "lng": 51.5060,
        "price_from_qar": 2500,
        "age_groups": ["0-2", "3-5"],
        "description": (
            "Nurturing environment rooted in Islamic values and the Early Years "
            "Foundation Stage, serving families in Al Sadd since 2018."
        ),
        "highlights": [
            "Islamic values integrated into daily routine",
            "Quran recitation circle",
            "Nutritionist-approved halal meals",
        ],
        "rating": Decimal("4.5"),
        "review_count": 42,
        "is_featured": False,
        "image_count": 2,
    },
    # ── ACTIVITIES (6) ───────────────────────────────────────────────────────
    {
        "slug": "activities-aspire-football-academy",
        "title": "Aspire Football Academy",
        "category": ListingCategory.ACTIVITIES,
        "subtitle": "Grassroots to elite football coaching, Aspire Zone",
        "neighborhood": "Aspire Zone",
        "lat": 25.2665,
        "lng": 51.4405,
        "price_from_qar": 250,
        "age_groups": ["6-9", "10-12", "13-17"],
        "description": (
            "Professional football coaching for all levels adjacent to the Aspire Dome, "
            "run by UEFA-licensed coaches."
        ),
        "highlights": [
            "UEFA-licensed coaching staff",
            "Access to Aspire Zone pitches",
            "Monthly performance analysis",
            "Tournament pathways",
        ],
        "rating": Decimal("4.8"),
        "review_count": 196,
        "is_featured": True,
        "image_count": 3,
    },
    {
        "slug": "activities-katara-arts-studio",
        "title": "Katara Arts Studio",
        "category": ListingCategory.ACTIVITIES,
        "subtitle": "Painting, ceramics & calligraphy for all ages",
        "neighborhood": "Katara",
        "lat": 25.3600,
        "lng": 51.5260,
        "price_from_qar": 150,
        "age_groups": ["6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Creative arts studio in the Katara Cultural Village offering painting, "
            "ceramics, and Arabic calligraphy classes for all ages."
        ),
        "highlights": [
            "Studio inside Katara Cultural Village",
            "Arabic calligraphy master classes",
            "Term-end gallery exhibition",
        ],
        "rating": Decimal("4.6"),
        "review_count": 89,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "activities-pearl-swim-club",
        "title": "Pearl Swim Club",
        "category": ListingCategory.ACTIVITIES,
        "subtitle": "Competitive & recreational swimming, The Pearl",
        "neighborhood": "The Pearl",
        "lat": 25.3705,
        "lng": 51.5520,
        "price_from_qar": 180,
        "age_groups": ["3-5", "6-9", "10-12", "13-17"],
        "description": (
            "Year-round swimming programme from beginner splash classes to "
            "competitive squad training, led by FINA-certified coaches."
        ),
        "highlights": [
            "FINA-certified coaches",
            "Heated 25m pool",
            "Competitive squad + recreational streams",
        ],
        "rating": Decimal("4.5"),
        "review_count": 73,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "activities-msheireb-dance-academy",
        "title": "Msheireb Dance Academy",
        "category": ListingCategory.ACTIVITIES,
        "subtitle": "Ballet, contemporary & Khaleeji dance",
        "neighborhood": "Msheireb Downtown",
        "lat": 25.2870,
        "lng": 51.5340,
        "price_from_qar": 200,
        "age_groups": ["3-5", "6-9", "10-12", "13-17"],
        "description": (
            "Professional dance studio in the heart of Msheireb Downtown "
            "offering classical ballet, contemporary, and traditional Khaleeji dance."
        ),
        "highlights": [
            "RAD-certified ballet curriculum",
            "Traditional Khaleeji dance classes",
            "Annual winter showcase",
        ],
        "rating": Decimal("4.7"),
        "review_count": 61,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "activities-al-gharrafa-tennis-club",
        "title": "Al Gharrafa Junior Tennis Club",
        "category": ListingCategory.ACTIVITIES,
        "subtitle": "ITF-pathway tennis for kids and teens",
        "neighborhood": "Al Gharrafa",
        "lat": 25.3110,
        "lng": 51.4760,
        "price_from_qar": 220,
        "age_groups": ["6-9", "10-12", "13-17"],
        "description": (
            "Structured ITF junior tennis pathway with certified coaches, "
            "catering to beginners through tournament-ready players."
        ),
        "highlights": [
            "ITF junior pathway",
            "6 floodlit clay courts",
            "Weekly match-play sessions",
        ],
        "rating": Decimal("4.4"),
        "review_count": 48,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "activities-rayyan-horse-riding",
        "title": "Al Rayyan Horse Riding School",
        "category": ListingCategory.ACTIVITIES,
        "subtitle": "Equestrian lessons for children and adults",
        "neighborhood": "Al Rayyan",
        "lat": 25.2600,
        "lng": 51.4100,
        "price_from_qar": 350,
        "age_groups": ["6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Family-friendly equestrian centre on the outskirts of Al Rayyan "
            "offering beginner through advanced riding lessons."
        ),
        "highlights": [
            "BHS-qualified instructors",
            "Pony rides for young children",
            "Desert trail rides (adults)",
        ],
        "rating": Decimal("4.6"),
        "review_count": 55,
        "is_featured": False,
        "image_count": 2,
    },
    # ── ENTERTAINMENT (3) ────────────────────────────────────────────────────
    {
        "slug": "entertainment-souq-waqif-adventures",
        "title": "Souq Waqif Family Adventures",
        "category": ListingCategory.ENTERTAINMENT,
        "subtitle": "Guided cultural & culinary tours of Souq Waqif",
        "neighborhood": "Souq Waqif",
        "lat": 25.2872,
        "lng": 51.5338,
        "price_from_qar": 80,
        "age_groups": ["6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Immersive guided family tours of Doha's historic Souq Waqif, "
            "blending Qatari heritage storytelling with hands-on culinary stops."
        ),
        "highlights": [
            "Expert Qatari heritage guides",
            "Traditional food tasting included",
            "Falconry demonstration option",
        ],
        "rating": Decimal("4.8"),
        "review_count": 134,
        "is_featured": True,
        "image_count": 3,
    },
    {
        "slug": "entertainment-lusail-family-bowling",
        "title": "Lusail Family Bowling & Games",
        "category": ListingCategory.ENTERTAINMENT,
        "subtitle": "16-lane bowling + arcade, Lusail Marina",
        "neighborhood": "Lusail",
        "lat": 25.4285,
        "lng": 51.5325,
        "price_from_qar": 50,
        "age_groups": ["3-5", "6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Modern 16-lane bowling alley with bumper options for young children, "
            "plus a 200-game arcade floor at Lusail Marina."
        ),
        "highlights": [
            "16 lanes with bumper rails for kids",
            "200-game arcade floor",
            "Birthday party packages",
        ],
        "rating": Decimal("4.3"),
        "review_count": 201,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "entertainment-old-airport-go-karts",
        "title": "Old Airport Go-Kart Arena",
        "category": ListingCategory.ENTERTAINMENT,
        "subtitle": "Indoor & outdoor kart racing for all ages",
        "neighborhood": "Old Airport",
        "lat": 25.2670,
        "lng": 51.5450,
        "price_from_qar": 120,
        "age_groups": ["6-9", "10-12", "13-17", "Adults"],
        "description": (
            "High-energy go-kart venue with separate junior and adult tracks, "
            "electric karts, and a café pit lane."
        ),
        "highlights": [
            "Separate junior & adult tracks",
            "Electric karts (eco-friendly)",
            "Lap timing & leaderboard",
        ],
        "rating": Decimal("4.2"),
        "review_count": 168,
        "is_featured": False,
        "image_count": 2,
    },
    # ── TUTORING (3) ─────────────────────────────────────────────────────────
    {
        "slug": "tutoring-qatari-arabic-tutors",
        "title": "Qatari Arabic Tutors",
        "category": ListingCategory.TUTORING,
        "subtitle": "Native Arabic tutors for all curricula",
        "neighborhood": "Al Sadd",
        "lat": 25.2800,
        "lng": 51.5070,
        "price_from_qar": 120,
        "age_groups": ["6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Network of vetted native Arabic-speaking tutors covering MSA, "
            "Qatari dialect, and school-curriculum Arabic for all levels."
        ),
        "highlights": [
            "Native Qatari and Arab tutors",
            "Covers MSA, dialect & exam prep",
            "Online or in-home sessions",
        ],
        "rating": Decimal("4.7"),
        "review_count": 93,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "tutoring-stem-edge-tutoring",
        "title": "STEM Edge Tutoring",
        "category": ListingCategory.TUTORING,
        "subtitle": "Maths, Physics & Computer Science tutors, West Bay",
        "neighborhood": "West Bay",
        "lat": 25.3210,
        "lng": 51.5265,
        "price_from_qar": 150,
        "age_groups": ["6-9", "10-12", "13-17"],
        "description": (
            "Specialist tutors for IGCSE, IB, and A-Level Maths, Physics, "
            "and Computer Science, with a strong track record of grade uplift."
        ),
        "highlights": [
            "A-Level / IB / IGCSE specialists",
            "Small group (max 4) or 1-on-1",
            "Free diagnostic assessment",
        ],
        "rating": Decimal("4.8"),
        "review_count": 117,
        "is_featured": True,
        "image_count": 2,
    },
    {
        "slug": "tutoring-language-bridge-centre",
        "title": "Language Bridge Centre",
        "category": ListingCategory.TUTORING,
        "subtitle": "English, French & Spanish for school & IELTS prep",
        "neighborhood": "Education City",
        "lat": 25.3160,
        "lng": 51.4368,
        "price_from_qar": 100,
        "age_groups": ["6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Accredited language tutoring centre offering English, French, and Spanish "
            "for school support and internationally recognised exams."
        ),
        "highlights": [
            "IELTS / DELF / DELE exam prep",
            "Cambridge Young Learners pathway",
            "Native-speaker tutors",
        ],
        "rating": Decimal("4.5"),
        "review_count": 76,
        "is_featured": False,
        "image_count": 2,
    },
    # ── MASTERCLASSES (3) ────────────────────────────────────────────────────
    {
        "slug": "masterclasses-master-the-oud",
        "title": "Master the Oud Workshop",
        "category": ListingCategory.MASTERCLASSES,
        "subtitle": "Traditional oud from beginner to concert level",
        "neighborhood": "Katara",
        "lat": 25.3603,
        "lng": 51.5258,
        "price_from_qar": 300,
        "age_groups": ["13-17", "Adults"],
        "description": (
            "Intensive oud lessons taught by award-winning Qatari musician "
            "Ahmed Al-Marri, held inside the Katara Cultural Village."
        ),
        "highlights": [
            "Taught by award-winning oud master",
            "Instrument loan available",
            "Recital performance at term end",
        ],
        "rating": Decimal("4.9"),
        "review_count": 44,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "masterclasses-doha-culinary-studio",
        "title": "Doha Culinary Studio",
        "category": ListingCategory.MASTERCLASSES,
        "subtitle": "Qatari & Mediterranean cooking masterclasses",
        "neighborhood": "Msheireb Downtown",
        "lat": 25.2875,
        "lng": 51.5345,
        "price_from_qar": 250,
        "age_groups": ["13-17", "Adults"],
        "description": (
            "Hands-on cooking masterclasses focused on traditional Qatari "
            "recipes and Mediterranean cuisine, led by professional chefs."
        ),
        "highlights": [
            "Traditional Qatari recipe masterclasses",
            "Professional kitchen equipment",
            "Take home what you cook",
        ],
        "rating": Decimal("4.7"),
        "review_count": 58,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "masterclasses-photography-doha",
        "title": "Doha Street Photography Masterclass",
        "category": ListingCategory.MASTERCLASSES,
        "subtitle": "Urban & landscape photography in Doha's best spots",
        "neighborhood": "Souq Waqif",
        "lat": 25.2860,
        "lng": 51.5330,
        "price_from_qar": 400,
        "age_groups": ["13-17", "Adults"],
        "description": (
            "Weekend photography masterclasses led by published Doha photographer "
            "covering composition, light, and post-processing on location."
        ),
        "highlights": [
            "On-location shooting in Souq & West Bay",
            "Lightroom post-processing session",
            "Printed portfolio at end of course",
        ],
        "rating": Decimal("4.6"),
        "review_count": 37,
        "is_featured": False,
        "image_count": 2,
    },
    # ── PARTNERSHIPS (2) ─────────────────────────────────────────────────────
    {
        "slug": "partnerships-qf-family-pass",
        "title": "Qatar Foundation Family Pass",
        "category": ListingCategory.PARTNERSHIPS,
        "subtitle": "Discounted access to QF campus events & attractions",
        "neighborhood": "Education City",
        "lat": 25.3150,
        "lng": 51.4355,
        "price_from_qar": 0,
        "age_groups": ["0-2", "3-5", "6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Exclusive Sabil Life partnership granting registered families "
            "discounted entry to Qatar Foundation campus events, museums, and parks."
        ),
        "highlights": [
            "Free entry to QF Science Museum",
            "Discounted HBKU lecture series tickets",
            "Family picnic areas access",
        ],
        "rating": Decimal("4.5"),
        "review_count": 29,
        "is_featured": False,
        "image_count": 2,
    },
    {
        "slug": "partnerships-aspire-zone-family",
        "title": "Aspire Zone Family Membership",
        "category": ListingCategory.PARTNERSHIPS,
        "subtitle": "All-access family membership to Aspire Zone facilities",
        "neighborhood": "Aspire Zone",
        "lat": 25.2658,
        "lng": 51.4395,
        "price_from_qar": 500,
        "age_groups": ["0-2", "3-5", "6-9", "10-12", "13-17", "Adults"],
        "description": (
            "Special family membership rate negotiated by Sabil Life giving "
            "unlimited access to Aspire Zone gyms, pools, and track facilities."
        ),
        "highlights": [
            "Olympic pool & gym access",
            "Free bike hire on the track",
            "10% off Aspire Zone café",
        ],
        "rating": Decimal("4.8"),
        "review_count": 83,
        "is_featured": True,
        "image_count": 2,
    },
]

# Sanity-check the data at import time (not at runtime in production — only in tests)
_EXPECTED_TOTALS = {
    ListingCategory.SCHOOLS: 4,
    ListingCategory.NURSERIES: 3,
    ListingCategory.ACTIVITIES: 6,
    ListingCategory.ENTERTAINMENT: 3,
    ListingCategory.TUTORING: 3,
    ListingCategory.MASTERCLASSES: 3,
    ListingCategory.PARTNERSHIPS: 2,
}
assert len(LISTINGS) == 24, f"Expected 24 listings, got {len(LISTINGS)}"


class Command(BaseCommand):
    help = (
        "Seed the catalog with 24 Doha listings mirroring the Flutter mock dataset. "
        "Safe to run multiple times — idempotent via deterministic UUIDs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help=(
                "Delete all seeded listings (matched by deterministic UUID) "
                "before re-seeding. Provider-created listings outside the seed "
                "set are never touched."
            ),
        )
        parser.add_argument(
            "--count",
            action="store_true",
            help="Print how many would be inserted vs already exist; no writes.",
        )

    def handle(self, *args, **options):
        if options["count"]:
            self._handle_count()
            return

        if options["clean"]:
            seed_ids = [_uid(d["slug"]) for d in LISTINGS]
            deleted, _ = Listing.objects.filter(id__in=seed_ids).delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted} previously-seeded listing(s).")
            )

        # Upsert the two seed provider users so TUTORING / MASTERCLASSES
        # listings have a valid owner. Other categories stay owner=None
        # since they don't participate in the inquiry/subscription flows.
        tutor_owner = _get_or_create_seed_provider(
            SEED_TUTOR_EMAIL, UserRole.TUTOR, "Tutor"
        )
        mc_owner = _get_or_create_seed_provider(
            SEED_MC_EMAIL, UserRole.MASTERCLASS, "Masterclass"
        )
        category_owner = {
            ListingCategory.TUTORING: tutor_owner,
            ListingCategory.MASTERCLASSES: mc_owner,
        }

        created_count = 0
        existed_count = 0

        for data in LISTINGS:
            slug = data["slug"]
            listing_id = _uid(slug)
            defaults = {
                "title": data["title"],
                "category": data["category"],
                "subtitle": data["subtitle"],
                "neighborhood": data["neighborhood"],
                "lat": data["lat"],
                "lng": data["lng"],
                "price_from_qar": data["price_from_qar"],
                "age_groups": data["age_groups"],
                "description": data["description"],
                "highlights": data["highlights"],
                "rating": data["rating"],
                "review_count": data["review_count"],
                "is_featured": data["is_featured"],
                "status": ListingStatus.ACTIVE,
                "owner": category_owner.get(data["category"]),
            }
            listing, created = Listing.objects.update_or_create(
                id=listing_id, defaults=defaults
            )
            if created:
                created_count += 1
                self._seed_images(listing, slug, data.get("image_count", 1))
            else:
                existed_count += 1


        # Summary breakdown
        from collections import Counter

        cat_counts = Counter(d["category"] for d in LISTINGS)
        breakdown = ", ".join(
            f"{count} {cat}" for cat, count in sorted(cat_counts.items())
        )
        total = created_count + existed_count
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {total} listings "
                f"({created_count} created, {existed_count} already existed). "
                f"Breakdown: {breakdown}."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seed providers: "
                f"{SEED_TUTOR_EMAIL} (TUTOR) / "
                f"{SEED_MC_EMAIL} (MASTERCLASS) "
                f"— password '{SEED_PROVIDER_PASSWORD}' (dev only)."
            )
        )

    def _seed_images(self, listing: Listing, slug: str, count: int) -> None:
        """Attach up to `count` placeholder images to a freshly-created listing.

        Best-effort: any image that can't be fetched is skipped so seeding
        still succeeds offline. Positions stay contiguous from 0 to satisfy
        the (listing, position) unique constraint.
        """
        position = 0
        for index in range(1, count + 1):
            content = _fetch_image(slug, index)
            if content is None:
                continue
            object_name = f"listings/{listing.id}/{uuid.uuid4().hex}.jpg"
            key = default_storage.save(object_name, content)
            ListingImage.objects.create(
                listing=listing, key=key, position=position
            )
            position += 1

    def _handle_count(self):
        existing_ids = set(
            Listing.objects.filter(
                id__in=[_uid(d["slug"]) for d in LISTINGS]
            ).values_list("id", flat=True)
        )
        would_create = sum(1 for d in LISTINGS if _uid(d["slug"]) not in existing_ids)
        already_exist = len(LISTINGS) - would_create
        self.stdout.write(
            f"Would insert: {would_create}  |  Already exist: {already_exist}  "
            f"|  Total in dataset: {len(LISTINGS)}"
        )
