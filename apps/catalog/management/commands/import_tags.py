"""import_tags management command — seeds the SCHOOLS tag vocabulary.

Independent of ``import_schools`` but ordered before it: ``import_schools``
links listings to tags by name and will refuse to run if a name it needs is
missing, so run this one first.

Idempotency: ``get_or_create`` on (name, category), which is exactly the
model's ``unique_tag_per_category`` constraint. Safe to re-run; re-running
after adding names to ``SCHOOL_TAG_FACETS`` inserts only the new ones.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import ListingCategory, ListingTag, ListingTagGroup
from apps.catalog.seed_data.school_tags import SCHOOL_TAG_FACETS, SCHOOL_TAGS

CATEGORY = ListingCategory.SCHOOLS


class Command(BaseCommand):
    help = (
        "Import the SCHOOLS listing-tag vocabulary (curriculum, qualification, "
        "stage, gender, network, character, facilities, fee band). Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help=(
                "Delete every SCHOOLS tag before importing. This detaches the "
                "tags from any listing that referenced them (the M2M rows go "
                "with them), so re-run import_schools afterwards to relink."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be created or removed; write nothing.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        existing = set(
            ListingTag.objects.filter(category=CATEGORY).values_list(
                "name", flat=True
            )
        )
        wanted = set(SCHOOL_TAGS)
        missing = [n for n in SCHOOL_TAGS if n not in existing]
        # Tags in the DB that the dataset no longer defines — surfaced, never
        # auto-deleted, because a manager may have added them by hand in admin.
        orphans = sorted(existing - wanted)

        if dry_run:
            self.stdout.write(
                f"Would create {len(missing)} tag(s); "
                f"{len(wanted) - len(missing)} already exist."
            )
            for name in missing:
                self.stdout.write(f"  + {name}")
            self._report_orphans(orphans)
            return

        if options["clean"]:
            # Report the ListingTag count only — the total returned by delete()
            # also counts cascaded listing-tag link rows.
            _, per_model = ListingTag.objects.filter(category=CATEGORY).delete()
            self.stdout.write(
                self.style.WARNING(
                    f"Deleted {per_model.get('catalog.ListingTag', 0)} "
                    f"SCHOOLS tag(s) and "
                    f"{per_model.get('catalog.Listing_tags', 0)} listing link(s)."
                )
            )
            existing = set()

        created_count = 0

        for group_order, (facet, names) in enumerate(SCHOOL_TAG_FACETS.items()):
            group, _ = ListingTagGroup.objects.update_or_create(
                category=CATEGORY,
                name=facet,
                defaults={
                    "order": group_order,
                },
            )

            for tag_order, name in enumerate(names):
                _, created = ListingTag.objects.update_or_create(
                    name=name,
                    category=CATEGORY,
                    defaults={
                        "group": group,
                        "order": tag_order,
                    },
                )
                if created:
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(wanted)} SCHOOLS tag(s) across "
                f"{len(SCHOOL_TAG_FACETS)} facet(s) "
                f"({created_count} created, {len(wanted) - created_count} "
                f"already existed)."
            )
        )
        for facet, names in SCHOOL_TAG_FACETS.items():
            self.stdout.write(f"  {facet}: {len(names)}")
        self._report_orphans(orphans)

    def _report_orphans(self, orphans: list[str]) -> None:
        if not orphans:
            return
        self.stdout.write(
            self.style.WARNING(
                f"{len(orphans)} SCHOOLS tag(s) exist in the DB but are not in "
                f"the dataset (left untouched): {', '.join(orphans)}"
            )
        )
