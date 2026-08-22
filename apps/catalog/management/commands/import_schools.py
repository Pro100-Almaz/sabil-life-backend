"""import_schools management command — seeds the Qatar schools dataset.

Run ``import_tags`` first; this command links each listing to its tags by name
and aborts if any name is missing rather than silently creating half-tagged
listings.

Idempotency follows ``seed_catalog``: ``update_or_create`` keyed on a
deterministic ``uuid5(NAMESPACE, slug)``, so re-running updates changed fields
instead of duplicating rows. The namespace is distinct from ``seed_catalog``'s,
so the two datasets can never collide on an id.

Coordinates use the best available school, address, road, or district location.
The supplied textual address is preserved separately in ``exact_address``.

Why status=ACTIVE and owner=None: schools are editorial catalog data, not
provider-submitted listings. The public ``/api/v1/listings/`` endpoint filters
``status=ACTIVE``, and ``get_queryset`` excludes ``owner=request.user`` — so
attaching an owner would hide all 84 schools from whoever owned them.
"""

import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import (
    Listing,
    ListingStatus,
    ListingTag,
)
from apps.catalog.seed_data.schools import CATEGORY, SCHOOLS

# Fixed namespace — changing this orphans every previously-imported school.
# Deliberately different from seed_catalog.NAMESPACE.
NAMESPACE = uuid.UUID("5ab11c00-0000-4000-8000-5c400015ab11")


def _uid(slug: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, slug)


class Command(BaseCommand):
    help = (
        "Import the Qatar schools from the SabilLife schools dataset as "
        "ACTIVE, owner-less SCHOOLS listings with tags attached. Idempotent. "
        "Run import_tags first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help=(
                "Delete previously-imported schools (matched by deterministic "
                "UUID) before importing. Listings outside this dataset — "
                "including provider-created ones — are never touched."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created/updated; write nothing.",
        )
        parser.add_argument(
            "--skip-tags",
            action="store_true",
            help=(
                "Import listings without linking tags, and do not require the "
                "tag vocabulary to exist yet."
            ),
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self._handle_dry_run(skip_tags=options["skip_tags"])
            return

        tag_map = {} if options["skip_tags"] else self._load_tag_map()

        with transaction.atomic():
            if options["clean"]:
                seed_ids = [_uid(s["slug"]) for s in SCHOOLS]
                # Report the Listing count only — the total returned by delete()
                # also counts cascaded tag-link rows, which reads as nonsense.
                _, per_model = Listing.objects.filter(id__in=seed_ids).delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Deleted {per_model.get('catalog.Listing', 0)} "
                        f"previously-imported school(s)."
                    )
                )

            created_count = 0
            updated_count = 0

            for data in SCHOOLS:
                listing, created = Listing.objects.update_or_create(
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
                    # set() so a re-run after a tag change drops stale links.
                    listing.tags.set(tag_map[t] for t in data["tags"])

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(SCHOOLS)} school(s) "
                f"({created_count} created, {updated_count} updated) "
                f"as status={ListingStatus.ACTIVE}, owner=None."
            )
        )
        if options["skip_tags"]:
            self.stdout.write(
                self.style.WARNING(
                    "--skip-tags: no tags linked. Run import_tags, then re-run "
                    "this command without --skip-tags to attach them."
                )
            )
        else:
            link_count = sum(len(s["tags"]) for s in SCHOOLS)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Linked {link_count} tag(s) "
                    f"({link_count / len(SCHOOLS):.1f} per school)."
                )
            )
        self.stdout.write(f"Coordinates: all {len(SCHOOLS)} school(s) placed.")

    def _load_tag_map(self) -> dict[str, ListingTag]:
        """Resolve every tag name the dataset needs, or abort listing what's missing."""
        needed = {t for s in SCHOOLS for t in s["tags"]}
        tag_map = {
            tag.name: tag
            for tag in ListingTag.objects.filter(category=CATEGORY, name__in=needed)
        }
        missing = sorted(needed - set(tag_map))
        if missing:
            raise CommandError(
                f"{len(missing)} required SCHOOLS tag(s) are missing: "
                f"{', '.join(missing)}.\n"
                "Run `python manage.py import_tags` first, or pass --skip-tags "
                "to import the listings untagged."
            )
        return tag_map

    def _handle_dry_run(self, *, skip_tags: bool) -> None:
        existing = set(
            Listing.objects.filter(id__in=[_uid(s["slug"]) for s in SCHOOLS]).values_list(
                "id", flat=True
            )
        )
        would_create = sum(1 for s in SCHOOLS if _uid(s["slug"]) not in existing)
        self.stdout.write(
            f"Would create: {would_create}  |  "
            f"Would update: {len(SCHOOLS) - would_create}  |  "
            f"Total in dataset: {len(SCHOOLS)}"
        )
        if skip_tags:
            return
        needed = {t for s in SCHOOLS for t in s["tags"]}
        present = set(
            ListingTag.objects.filter(category=CATEGORY, name__in=needed).values_list(
                "name", flat=True
            )
        )
        missing = sorted(needed - present)
        if missing:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(missing)} required tag(s) missing — import_tags has "
                    f"not been run: {', '.join(missing)}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"All {len(needed)} required tag(s) present.")
            )
