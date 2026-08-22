from django.core.management import call_command
from django.test import TestCase

from apps.catalog.management.commands.import_nurseries import _uid
from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.catalog.seed_data.nurseries import NURSERIES


class ImportNurseriesTests(TestCase):
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
        call_command("import_nurseries")
        call_command("import_nurseries")

        listings = Listing.objects.filter(
            id__in=[_uid(item["slug"]) for item in NURSERIES]
        )
        self.assertEqual(listings.count(), 90)
        self.assertFalse(listings.exclude(category=ListingCategory.NURSERIES).exists())
        self.assertFalse(listings.exclude(status=ListingStatus.ACTIVE).exists())

    def test_dry_run_does_not_write(self):
        call_command("import_nurseries", dry_run=True)
        self.assertFalse(
            Listing.objects.filter(
                id__in=[_uid(item["slug"]) for item in NURSERIES]
            ).exists()
        )
