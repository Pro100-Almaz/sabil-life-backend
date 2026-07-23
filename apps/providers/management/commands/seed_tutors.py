"""
seed_tutors management command.

Creates a set of individual tutor accounts, each a CustomUser (role=TUTOR)
with a matching providers.TutorDetail profile, so the family browse / inquiry
flow has real, richly-populated tutors to list and inquire against.

Idempotency: users are looked up by their stable seed email and TutorDetail
rows are upserted via update_or_create(user=...). Safe to run repeatedly — it
refreshes profile fields when the seed data changes and never duplicates rows.

Some tutors are affiliated to the seeded TUTORING listings created by
`seed_catalog` (via the listing's deterministic UUID) so the two datasets line
up; the rest are unaffiliated independent tutors.
"""

import uuid
from decimal import Decimal

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.management.commands.seed_catalog import _uid
from apps.providers.models import AvatarImage, TutorDetail, TutorSubject
from apps.users.enums import UserRole
from apps.users.models import CustomUser

# Password usable in dev, mirrors the seed providers in seed_catalog.py.
SEED_TUTOR_PASSWORD = "testpass123"

# Slugs of the TUTORING listings created by seed_catalog, used to compute the
# deterministic listing UUID that a tutor is affiliated to. `None` = independent
# tutor not attached to any seeded listing.
_ARABIC = "tutoring-qatari-arabic-tutors"
_STEM = "tutoring-stem-edge-tutoring"
_LANG = "tutoring-language-bridge-centre"


def _fetch_avatar(seed: str) -> ContentFile | None:
    """Best-effort fetch of a deterministic avatar photo for a tutor.

    pravatar returns the same face for a given `u` seed, so re-seeding a tutor
    yields a stable image. Returns None when the fetch fails (e.g. offline / in
    CI) — callers skip on None so seeding never breaks on a network error,
    mirroring `_fetch_image` in seed_catalog.
    """
    url = f"https://i.pravatar.cc/400?u={seed}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return ContentFile(resp.content)
    except requests.RequestException:
        return None


# ---------------------------------------------------------------------------
# Tutor data — 10 individual tutors, easy to scan / review
# ---------------------------------------------------------------------------
TUTORS: list[dict] = [
    {
        "email": "seed-tutor-amina-hassan@sabil.local",
        "full_name": "Amina Hassan",
        "affiliation_slug": _ARABIC,
        "subjects": ["Arabic (MSA)", "Quran", "Islamic Studies"],
        "formats": ["ONE_ON_ONE", "ONLINE"],
        "age_groups": ["6-12", "13-18"],
        "price_per_hour_qar": 120,
        "rating": Decimal("4.8"),
        "review_count": 41,
        "years_experience": 9,
        "credentials": "BA Arabic Literature, Qatar University; licensed teacher",
        "languages": ["AR", "EN"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "Native Qatari Arabic teacher specialising in Modern Standard Arabic "
            "and Quran recitation for school-age learners, online or in-home."
        ),
    },
    {
        "email": "seed-tutor-omar-al-kuwari@sabil.local",
        "full_name": "Omar Al-Kuwari",
        "affiliation_slug": _STEM,
        "subjects": ["Mathematics", "Physics"],
        "formats": ["ONE_ON_ONE", "SMALL_GROUP"],
        "age_groups": ["13-18"],
        "price_per_hour_qar": 180,
        "rating": Decimal("4.9"),
        "review_count": 63,
        "years_experience": 12,
        "credentials": "MSc Physics, Imperial College London",
        "languages": ["EN", "AR"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "A-Level and IB Maths & Physics specialist with a strong record of "
            "grade uplift. Small groups of up to four or one-to-one."
        ),
    },
    {
        "email": "seed-tutor-sara-mansour@sabil.local",
        "full_name": "Sara Mansour",
        "affiliation_slug": _LANG,
        "subjects": ["English", "IELTS Preparation"],
        "formats": ["ONE_ON_ONE", "ONLINE", "AT_CENTRE"],
        "age_groups": ["13-18", "Adult"],
        "price_per_hour_qar": 150,
        "rating": Decimal("4.7"),
        "review_count": 55,
        "years_experience": 8,
        "credentials": "CELTA certified; BA English, AUB",
        "languages": ["EN", "FR", "AR"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "Native-level English tutor focused on IELTS and academic writing for "
            "teens and adults preparing for university abroad."
        ),
    },
    {
        "email": "seed-tutor-yusuf-rahman@sabil.local",
        "full_name": "Yusuf Rahman",
        "affiliation_slug": _STEM,
        "subjects": ["Computer Science", "Mathematics"],
        "formats": ["ONE_ON_ONE", "ONLINE"],
        "age_groups": ["13-18"],
        "price_per_hour_qar": 200,
        "rating": Decimal("4.8"),
        "review_count": 37,
        "years_experience": 6,
        "credentials": "BSc Computer Science, University College London",
        "languages": ["EN"],
        "trial_available": False,
        "city": "Doha",
        "bio": (
            "IGCSE and A-Level Computer Science tutor covering Python, algorithms, "
            "and exam technique, with project-based online sessions."
        ),
    },
    {
        "email": "seed-tutor-fatima-al-thani@sabil.local",
        "full_name": "Fatima Al-Thani",
        "affiliation_slug": _ARABIC,
        "subjects": ["Arabic (MSA)", "Qatari Dialect"],
        "formats": ["ONE_ON_ONE", "AT_CENTRE"],
        "age_groups": ["Adult"],
        "price_per_hour_qar": 140,
        "rating": Decimal("4.6"),
        "review_count": 28,
        "years_experience": 7,
        "credentials": "MA Applied Linguistics, Georgetown Qatar",
        "languages": ["AR", "EN"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "Helps expatriate professionals learn conversational Qatari dialect and "
            "Modern Standard Arabic for work and daily life."
        ),
    },
    {
        "email": "seed-tutor-daniel-okoro@sabil.local",
        "full_name": "Daniel Okoro",
        "affiliation_slug": None,
        "subjects": ["Chemistry", "Biology"],
        "formats": ["ONE_ON_ONE", "SMALL_GROUP", "ONLINE"],
        "age_groups": ["13-18"],
        "price_per_hour_qar": 170,
        "rating": Decimal("4.7"),
        "review_count": 44,
        "years_experience": 10,
        "credentials": "PhD Biochemistry; former IB examiner",
        "languages": ["EN"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "IB and A-Level Chemistry and Biology tutor and former examiner who "
            "teaches to the mark scheme without losing the concepts."
        ),
    },
    {
        "email": "seed-tutor-leila-haddad@sabil.local",
        "full_name": "Leila Haddad",
        "affiliation_slug": _LANG,
        "subjects": ["French", "DELF Preparation"],
        "formats": ["ONE_ON_ONE", "ONLINE"],
        "age_groups": ["6-12", "13-18"],
        "price_per_hour_qar": 130,
        "rating": Decimal("4.5"),
        "review_count": 22,
        "years_experience": 5,
        "credentials": "Native French speaker; DELF-DALF trained examiner",
        "languages": ["FR", "EN", "AR"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "French tutor for the French curriculum and DELF exam preparation, "
            "patient with young learners and beginners."
        ),
    },
    {
        "email": "seed-tutor-hiroshi-tanaka@sabil.local",
        "full_name": "Hiroshi Tanaka",
        "affiliation_slug": None,
        "subjects": ["Mathematics", "Economics"],
        "formats": ["ONE_ON_ONE", "ONLINE"],
        "age_groups": ["13-18", "Adult"],
        "price_per_hour_qar": 190,
        "rating": Decimal("4.9"),
        "review_count": 31,
        "years_experience": 11,
        "credentials": "MSc Economics, LSE",
        "languages": ["EN", "JP"],
        "trial_available": False,
        "city": "Doha",
        "bio": (
            "A-Level and IB Economics and Maths tutor with a data-driven, "
            "structured approach to essay and multiple-choice papers."
        ),
    },
    {
        "email": "seed-tutor-noura-al-sulaiti@sabil.local",
        "full_name": "Noura Al-Sulaiti",
        "affiliation_slug": _ARABIC,
        "subjects": ["Primary Tutoring", "Arabic (MSA)", "Mathematics"],
        "formats": ["ONE_ON_ONE", "AT_CENTRE"],
        "age_groups": ["3-5", "6-12"],
        "price_per_hour_qar": 110,
        "rating": Decimal("4.8"),
        "review_count": 49,
        "years_experience": 8,
        "credentials": "BEd Primary Education, Qatar University",
        "languages": ["AR", "EN"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "Early-years and primary specialist covering Arabic, Maths, and general "
            "homework support in a warm, encouraging way."
        ),
    },
    {
        "email": "seed-tutor-carlos-mendez@sabil.local",
        "full_name": "Carlos Mendez",
        "affiliation_slug": _LANG,
        "subjects": ["Spanish", "DELE Preparation"],
        "formats": ["ONE_ON_ONE", "ONLINE", "SMALL_GROUP"],
        "age_groups": ["13-18", "Adult"],
        "price_per_hour_qar": 125,
        "rating": Decimal("4.6"),
        "review_count": 19,
        "years_experience": 6,
        "credentials": "Native Spanish speaker; Instituto Cervantes certified",
        "languages": ["ES", "EN"],
        "trial_available": True,
        "city": "Doha",
        "bio": (
            "Spanish tutor for school support and DELE exam preparation, from "
            "absolute beginner to advanced conversation."
        ),
    },
]

_EXPECTED_COUNT = 10
assert len(TUTORS) == _EXPECTED_COUNT, (
    f"Expected {_EXPECTED_COUNT} tutors, got {len(TUTORS)}"
)


class Command(BaseCommand):
    help = (
        "Seed 10 individual tutor accounts (CustomUser + TutorDetail). "
        "Idempotent — safe to run repeatedly; looks up users by seed email."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help=(
                "Delete the seeded tutor users (matched by seed email) before "
                "re-seeding. Cascades to their TutorDetail rows. Non-seed users "
                "are never touched."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        emails = [t["email"] for t in TUTORS]

        if options["clean"]:
            deleted, _ = CustomUser.objects.filter(email__in=emails).delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted} previously-seeded tutor row(s).")
            )

        created_count = 0
        existed_count = 0
        avatar_count = 0

        for data in TUTORS:
            user, created = CustomUser.objects.get_or_create(
                email=data["email"],
                defaults={
                    "role": UserRole.TUTOR,
                    "full_name": data["full_name"],
                    "is_verified": True,
                    "is_active": True,
                },
            )
            if created:
                user.set_password(SEED_TUTOR_PASSWORD)
                user.save(update_fields=["password"])
                created_count += 1
            else:
                existed_count += 1

            affiliation_id = (
                str(_uid(data["affiliation_slug"])) if data["affiliation_slug"] else ""
            )
            tutor_detail, _ = TutorDetail.objects.update_or_create(
                user=user,
                defaults={
                    "affiliation_listing_id": affiliation_id,
                    "subjects": data["subjects"],
                    "formats": data["formats"],
                    "age_groups": data["age_groups"],
                    "price_per_hour_qar": data["price_per_hour_qar"],
                    "rating": data["rating"],
                    "review_count": data["review_count"],
                    "years_experience": data["years_experience"],
                    "credentials": data["credentials"],
                    "languages": data["languages"],
                    "trial_available": data["trial_available"],
                    "bio": data["bio"],
                    "is_verified": True,
                    "city": data["city"],
                },
            )

            if self._seed_avatar(tutor_detail, data["email"]):
                avatar_count += 1

        total = created_count + existed_count
        subject_names = {s for t in TUTORS for s in t["subjects"]}
        for name in subject_names:
            TutorSubject.objects.get_or_create(name=name)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {total} tutor accounts "
                f"({created_count} created, {existed_count} already existed), "
                f"{avatar_count} avatar(s) attached "
                f"— password '{SEED_TUTOR_PASSWORD}' (dev only)."
            )
        )

    def _seed_avatar(self, tutor_detail: TutorDetail, seed: str) -> bool:
        """Attach an avatar to a tutor that doesn't have one yet.

        Idempotent and best-effort: skips tutors that already have an avatar and
        returns False if the image can't be fetched, so re-runs don't refetch
        and offline seeding still succeeds. Returns True when a new avatar was
        saved.
        """
        if AvatarImage.objects.filter(tutor=tutor_detail).exists():
            return False
        content = _fetch_avatar(seed)
        if content is None:
            return False
        object_name = f"avatars/{tutor_detail.id}/{uuid.uuid4().hex}.jpg"
        key = default_storage.save(object_name, content)
        AvatarImage.objects.create(tutor=tutor_detail, key=key)
        return True
