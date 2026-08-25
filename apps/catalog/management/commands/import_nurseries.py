"""Import the editorial Qatar nursery and kindergarten dataset."""

import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Listing, ListingStatus, ListingTag
from apps.catalog.seed_data.nurseries import CATEGORY, NURSERIES
from apps.catalog.seed_data.nursery_tags import nursery_seed_tags

NAMESPACE = uuid.UUID("6ab11c00-0000-4000-8000-5c400015ab11")


def _uid(slug: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, slug)


class Command(BaseCommand):
    help = "Import 90 Qatar nursery and kindergarten listings. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete only previously imported nursery records before importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created or updated without writing.",
        )
        parser.add_argument(
            "--skip-tags",
            action="store_true",
            help="Import listings without linking nursery tags.",
        )

    def handle(self, *args, **options):
        tag_map = {} if options["skip_tags"] else self._load_tag_map()
        seed_ids = [_uid(item["slug"]) for item in NURSERIES]
        existing = set(
            Listing.objects.filter(id__in=seed_ids).values_list("id", flat=True)
        )
        create_count = sum(_uid(item["slug"]) not in existing for item in NURSERIES)

        if options["dry_run"]:
            self.stdout.write(
                f"Would create: {create_count}  |  "
                f"Would update: {len(NURSERIES) - create_count}  |  "
                f"Total in dataset: {len(NURSERIES)}"
            )
            return

        with transaction.atomic():
            if options["clean"]:
                Listing.objects.filter(id__in=seed_ids).delete()

            for data in NURSERIES:
                listing, _ = Listing.objects.update_or_create(
                    id=_uid(data["slug"]),
                    defaults={
                        "title": data["title"],
                        "category": CATEGORY,
                        "subtitle": data["subtitle"],
                        "neighborhood": data["neighborhood"],
                        "lat": data["lat"],
                        "lng": data["lng"],
                        "price_from_qar": data["price_from_qar"],
                        "age_groups": data["age_groups"],
                        "description": data["description"],
                        "highlights": data["highlights"],
                        "exact_address": data["exact_address"],
                        "is_featured": False,
                        "status": ListingStatus.ACTIVE,
                        "owner": None,
                    },
                )
                if not options["skip_tags"]:
                    listing.tags.set(tag_map[name] for name in nursery_seed_tags(data))

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(NURSERIES)} nursery listing(s) "
                f"({create_count} created, {len(NURSERIES) - create_count} updated)."
            )
        )

    def _load_tag_map(self) -> dict[str, ListingTag]:
        needed = {name for item in NURSERIES for name in nursery_seed_tags(item)}
        tag_map = {
            tag.name: tag
            for tag in ListingTag.objects.filter(category=CATEGORY, name__in=needed)
        }
        missing = sorted(needed - set(tag_map))
        if missing:
            raise CommandError(
                f"{len(missing)} required NURSERIES tag(s) are missing: "
                f"{', '.join(missing)}.\n"
                "Run `python manage.py import_nursery_tags` first, or pass "
                "--skip-tags to import the listings untagged."
            )
        return tag_map
