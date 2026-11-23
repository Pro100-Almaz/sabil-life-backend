from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.catalog.management.commands.import_entertainment import _uid
from apps.catalog.models import (
    Listing,
    ListingCategory,
    ListingContact,
    ListingContactType,
    ListingStatus,
)
from apps.catalog.seed_data.entertainment import ENTERTAINMENT


def _seed_ids():
    return [_uid(item["slug"]) for item in ENTERTAINMENT]


class ImportEntertainmentTests(TestCase):
    def _import(self, **kwargs):
        call_command("import_entertainment", stdout=StringIO(), **kwargs)

    def test_dataset_has_all_rows_with_unique_slugs_and_coordinates(self):
        self.assertEqual(len(ENTERTAINMENT), 15)
        self.assertEqual(len({item["slug"] for item in ENTERTAINMENT}), 15)
        self.assertTrue(all(item["lat"] and item["lng"] for item in ENTERTAINMENT))

    def test_import_creates_active_ownerless_listings(self):
        self._import()

        listings = Listing.objects.filter(id__in=_seed_ids())
        self.assertEqual(listings.count(), 15)
        self.assertFalse(
            listings.exclude(category=ListingCategory.ENTERTAINMENT).exists()
        )
        self.assertFalse(listings.exclude(status=ListingStatus.ACTIVE).exists())
        self.assertFalse(listings.exclude(owner=None).exists())

    def test_import_saves_contacts_in_order(self):
        self._import()

        listing = Listing.objects.get(id=_uid("entertainment-katara-cinema"))
        self.assertEqual(
            list(listing.contacts.values_list("contact_type", "value")),
            [
                (ListingContactType.PHONE, "+974 3139 3976"),
                (ListingContactType.INSTAGRAM, "https://instagram.com/katara.cinema"),
            ],
        )

    def test_reimport_is_idempotent(self):
        self._import()
        self._import()

        self.assertEqual(Listing.objects.filter(id__in=_seed_ids()).count(), 15)
        self.assertEqual(
            ListingContact.objects.filter(listing_id__in=_seed_ids()).count(),
            sum(len(item["contacts"]) for item in ENTERTAINMENT),
        )

    def test_clean_reimport_keeps_dataset_intact(self):
        self._import()
        self._import(clean=True)

        self.assertEqual(Listing.objects.filter(id__in=_seed_ids()).count(), 15)

    def test_dry_run_does_not_write(self):
        self._import(dry_run=True)

        self.assertFalse(Listing.objects.filter(id__in=_seed_ids()).exists())
