from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.catalog.management.commands.import_schools import _uid
from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.catalog.seed_data.schools import SCHOOLS


class ImportSchoolsTests(TestCase):
    def _import(self):
        call_command("import_tags", stdout=StringIO())
        call_command("import_schools", stdout=StringIO())

    def test_import_creates_complete_dataset(self):
        self._import()

        seed_ids = [_uid(school["slug"]) for school in SCHOOLS]
        listings = Listing.objects.filter(id__in=seed_ids)

        self.assertEqual(listings.count(), 97)
        self.assertFalse(listings.exclude(category=ListingCategory.SCHOOLS).exists())
        self.assertFalse(listings.exclude(status=ListingStatus.ACTIVE).exists())
        self.assertFalse(listings.exclude(owner=None).exists())

    def test_import_updates_renamed_school_without_duplicate(self):
        self._import()

        listing = Listing.objects.get(id=_uid("schools-doha-academy"))

        self.assertEqual(listing.title, "Doha Academy – Al Waab Campus")
        self.assertFalse(Listing.objects.filter(title="Doha Academy").exists())

    def test_dataset_splits_multiple_phone_numbers(self):
        school = next(
            item
            for item in SCHOOLS
            if item["slug"] == "schools-acs-international-school-doha"
        )

        self.assertEqual(school["phones"], ("+974 3026 6800", "+974 4474 9000"))

    def test_import_saves_exact_address(self):
        self._import()

        listing = Listing.objects.get(id=_uid("schools-acs-international-school-doha"))
        self.assertEqual(
            listing.exact_address,
            "Building No. 10, Street No. 161, Area/Zone 70, Al Kheesa, Qatar",
        )

    def test_reimport_is_idempotent(self):
        self._import()
        call_command("import_schools", stdout=StringIO())
        self.assertEqual(
            Listing.objects.filter(
                id__in=[_uid(school["slug"]) for school in SCHOOLS]
            ).count(),
            97,
        )

    def test_dry_run_writes_nothing(self):
        call_command("import_schools", dry_run=True, skip_tags=True, stdout=StringIO())

        self.assertEqual(Listing.objects.count(), 0)
