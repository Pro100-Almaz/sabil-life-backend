"""
Tests for the Listing model.

Covers: defaults, __str__, ordering, choices enforcement.
"""

from decimal import Decimal

import pytest

from apps.catalog.models import Listing, ListingCategory, ListingStatus


def make_listing(**kwargs) -> Listing:
    """Helper: build (and save) a minimal Listing with sensible defaults."""
    defaults = {
        "title": "Test Listing",
        "category": ListingCategory.TUTORING,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


@pytest.mark.django_db
class TestListingDefaults:
    def test_default_status_is_draft(self):
        listing = Listing.objects.create(
            title="Draft Listing",
            category=ListingCategory.SCHOOLS,
        )
        assert listing.status == ListingStatus.DRAFT

    def test_default_rating_is_zero(self):
        listing = make_listing()
        assert listing.rating == Decimal("0.0")

    def test_default_review_count_is_zero(self):
        listing = make_listing()
        assert listing.review_count == 0

    def test_default_price_from_qar_is_zero(self):
        listing = make_listing()
        assert listing.price_from_qar == 0

    def test_default_is_featured_false(self):
        listing = make_listing()
        assert listing.is_featured is False

    def test_default_age_groups_empty_list(self):
        listing = make_listing()
        assert listing.age_groups == []

    def test_default_highlights_empty_list(self):
        listing = make_listing()
        assert listing.highlights == []

    def test_id_is_uuid(self):
        import uuid

        listing = make_listing()
        # Should not raise
        uuid.UUID(str(listing.id))

    def test_owner_nullable(self):
        listing = make_listing()
        assert listing.owner is None


@pytest.mark.django_db
class TestListingStr:
    def test_str_returns_title_and_category(self):
        listing = make_listing(title="Bright Minds", category=ListingCategory.TUTORING)
        assert str(listing) == "Bright Minds (TUTORING)"

    def test_str_various_categories(self):
        for category, _ in ListingCategory.choices:
            listing = make_listing(title="X", category=category)
            assert category in str(listing)


@pytest.mark.django_db
class TestListingOrdering:
    def test_featured_listings_sort_before_non_featured(self):
        """Featured listings appear first regardless of created_at."""
        make_listing(title="Non-featured", is_featured=False)
        make_listing(title="Featured", is_featured=True)

        titles = list(Listing.objects.values_list("title", flat=True))
        assert titles.index("Featured") < titles.index("Non-featured")

    def test_newer_listings_sort_before_older_within_same_featured_status(self):
        """Among non-featured listings, newer ones come first."""
        make_listing(title="Older")
        make_listing(title="Newer")

        # Both non-featured; newer should precede older
        non_featured_titles = list(
            Listing.objects.filter(is_featured=False).values_list("title", flat=True)
        )
        assert non_featured_titles.index("Newer") < non_featured_titles.index("Older")


@pytest.mark.django_db
class TestListingChoices:
    def test_all_category_choices_exist(self):
        expected = {
            "SCHOOLS",
            "NURSERIES",
            "ACTIVITIES",
            "ENTERTAINMENT",
            "TUTORING",
            "MASTERCLASSES",
            "PARTNERSHIPS",
        }
        actual = {choice[0] for choice in ListingCategory.choices}
        assert actual == expected

    def test_all_status_choices_exist(self):
        expected = {"DRAFT", "PENDING", "ACTIVE", "REJECTED"}
        actual = {choice[0] for choice in ListingStatus.choices}
        assert actual == expected

    def test_listing_with_each_category_saves(self):
        for category, _ in ListingCategory.choices:
            listing = make_listing(title=f"Cat-{category}", category=category)
            assert listing.category == category

    def test_listing_with_each_status_saves(self):
        for i, (status_val, _) in enumerate(ListingStatus.choices):
            listing = make_listing(title=f"Status-{i}", status=status_val)
            assert listing.status == status_val
