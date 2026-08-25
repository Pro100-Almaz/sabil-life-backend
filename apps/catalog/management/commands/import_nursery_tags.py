"""Seed the grouped NURSERIES listing-tag vocabulary."""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import ListingCategory, ListingTag, ListingTagGroup
from apps.catalog.seed_data.nursery_tags import NURSERY_TAG_FACETS, NURSERY_TAGS

CATEGORY = ListingCategory.NURSERIES


class Command(BaseCommand):
    help = "Import the grouped NURSERIES listing-tag vocabulary. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete existing NURSERIES tags before importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created without writing.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        existing = set(
            ListingTag.objects.filter(category=CATEGORY).values_list("name", flat=True)
        )
        missing = [name for name in NURSERY_TAGS if name not in existing]

        if options["dry_run"]:
            self.stdout.write(
                f"Would create {len(missing)} tag(s); "
                f"{len(NURSERY_TAGS) - len(missing)} already exist."
            )
            return

        if options["clean"]:
            ListingTag.objects.filter(category=CATEGORY).delete()

        created_count = 0
        for group_order, (facet, names) in enumerate(NURSERY_TAG_FACETS.items()):
            group, _ = ListingTagGroup.objects.update_or_create(
                category=CATEGORY,
                name=facet,
                defaults={"order": group_order},
            )
            for tag_order, name in enumerate(names):
                _, created = ListingTag.objects.update_or_create(
                    category=CATEGORY,
                    name=name,
                    defaults={"group": group, "order": tag_order},
                )
                created_count += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(NURSERY_TAGS)} NURSERIES tag(s) across "
                f"{len(NURSERY_TAG_FACETS)} facet(s) ({created_count} created)."
            )
        )
