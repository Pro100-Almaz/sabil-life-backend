"""import_entertainment — seeds the Qatar entertainment venues dataset.

Same contract as ``import_schools`` / ``import_nurseries``: listings are
ACTIVE, owner-less editorial records upserted on a deterministic
``uuid5(NAMESPACE, slug)``, so re-running updates rows instead of duplicating.

Contacts (phone / website / Instagram) are upserted on the model's
``(listing, contact_type, value)`` unique key. Contacts added by hand in the
admin are left alone; pass ``--clean`` for a full reset of this dataset.

No tags are linked — there is no ENTERTAINMENT tag vocabulary yet.
"""

import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Listing, ListingContact, ListingStatus
from apps.catalog.seed_data.entertainment import CATEGORY, ENTERTAINMENT

# Fixed namespace — changing this orphans every previously-imported venue.
NAMESPACE = uuid.UUID("7ab11c00-0000-4000-8000-5c400015ab11")


def _uid(slug: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, slug)


class Command(BaseCommand):
    help = (
        f"Import {len(ENTERTAINMENT)} Qatar entertainment venues as ACTIVE, "
        "owner-less ENTERTAINMENT listings with contacts. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help=(
                "Delete previously-imported venues (matched by deterministic UUID) "
                "before importing. Other listings are never touched."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created/updated; write nothing.",
        )

    def handle(self, *args, **options):
        seed_ids = [_uid(item["slug"]) for item in ENTERTAINMENT]
        existing = set(
            Listing.objects.filter(id__in=seed_ids).values_list("id", flat=True)
        )
        create_count = sum(_uid(item["slug"]) not in existing for item in ENTERTAINMENT)

        if options["dry_run"]:
            self.stdout.write(
                f"Would create: {create_count}  |  "
                f"Would update: {len(ENTERTAINMENT) - create_count}  |  "
                f"Total in dataset: {len(ENTERTAINMENT)}"
            )
            return

        with transaction.atomic():
            if options["clean"]:
                _, per_model = Listing.objects.filter(id__in=seed_ids).delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Deleted {per_model.get('catalog.Listing', 0)} "
                        "previously-imported venue(s)."
                    )
                )
                create_count = len(ENTERTAINMENT)

            contact_count = 0
            for data in ENTERTAINMENT:
                listing, _ = Listing.objects.update_or_create(
                    id=_uid(data["slug"]),
                    defaults={
                        "title": data["title"],
                        "category": CATEGORY,
                        "subtitle": data["subtitle"],
                        "neighborhood": data["neighborhood"],
                        "lat": data["lat"],
                        "lng": data["lng"],
                        "price_from_qar": 0,
                        "age_groups": [],
                        "description": data["description"],
                        "highlights": data["highlights"],
                        "exact_address": data["exact_address"],
                        "is_featured": False,
                        "status": ListingStatus.ACTIVE,
                        "owner": None,
                    },
                )
                for position, (contact_type, value) in enumerate(data["contacts"]):
                    ListingContact.objects.update_or_create(
                        listing=listing,
                        contact_type=contact_type,
                        value=value,
                        defaults={"position": position},
                    )
                    contact_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(ENTERTAINMENT)} entertainment listing(s) "
                f"({create_count} created, {len(ENTERTAINMENT) - create_count} "
                f"updated) with {contact_count} contact(s)."
            )
        )
