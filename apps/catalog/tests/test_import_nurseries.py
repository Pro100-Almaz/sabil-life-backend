from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.catalog.management.commands.import_nurseries import _uid
from apps.catalog.models import Listing, ListingCategory, ListingStatus, ListingTag
from apps.catalog.seed_data.nurseries import NURSERIES
from apps.catalog.seed_data.nursery_tags import NURSERY_TAGS, nursery_seed_tags


class ImportNurseriesTests(TestCase):
    def _import(self):
        call_command("import_nursery_tags", stdout=StringIO())
        call_command("import_nurseries", stdout=StringIO())

    def test_dataset_preserves_all_rows_with_unique_slugs(self):
        self.assertEqual(len(NURSERIES), 90)
        self.assertEqual(len({item["slug"] for item in NURSERIES}), 90)
        self.assertTrue(all(item["lat"] is not None for item in NURSERIES))
        self.assertTrue(all(item["lng"] is not None for item in NURSERIES))

    def test_duplicate_apple_tree_rows_remain_separate(self):
        records = [item for item in NURSERIES if item["title"] == "Apple Tree Nursery"]
        self.assertEqual(len(records), 2)
        self.assertNotEqual(records[0]["slug"], records[1]["slug"])
        self.assertNotEqual(records[0]["phones"], records[1]["phones"])

    def test_missing_public_contacts_are_empty(self):
        record = next(
            item
            for item in NURSERIES
            if item["title"] == "Bright Horizon International Kindergarten"
        )
        self.assertEqual(record["phones"], ())

    def test_import_is_idempotent(self):
        self._import()
        call_command("import_nurseries", stdout=StringIO())

        listings = Listing.objects.filter(
            id__in=[_uid(item["slug"]) for item in NURSERIES]
        )
        self.assertEqual(listings.count(), 90)
        self.assertFalse(listings.exclude(category=ListingCategory.NURSERIES).exists())
        self.assertFalse(listings.exclude(status=ListingStatus.ACTIVE).exists())

    def test_import_links_only_tags_supported_by_seed_data(self):
        self._import()
        redwood = next(item for item in NURSERIES if "redwood-montessori" in item["slug"])
        listing = Listing.objects.get(id=_uid(redwood["slug"]))

        self.assertSetEqual(
            set(listing.tags.values_list("name", flat=True)),
            set(nursery_seed_tags(redwood)),
        )
        self.assertIn("Montessori", nursery_seed_tags(redwood))

    def test_nursery_tag_import_is_idempotent_and_grouped(self):
        call_command("import_nursery_tags", stdout=StringIO())
        call_command("import_nursery_tags", stdout=StringIO())

        tags = ListingTag.objects.filter(category=ListingCategory.NURSERIES)
        self.assertEqual(tags.count(), len(NURSERY_TAGS))
        self.assertFalse(tags.filter(group=None).exists())

    def test_dry_run_does_not_write(self):
        call_command("import_nurseries", dry_run=True, skip_tags=True)
        self.assertFalse(
            Listing.objects.filter(
                id__in=[_uid(item["slug"]) for item in NURSERIES]
            ).exists()
        )
