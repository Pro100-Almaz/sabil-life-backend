"""
Tests for the ServiceSuggestion model — defaults, choices.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import ListingCategory
from apps.suggestions.models import ServiceSuggestion, SuggestionStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


@pytest.mark.django_db
class TestServiceSuggestionModel:
    def test_default_status_is_new(self):
        family = make_user("fam_sug@test.com")
        suggestion = ServiceSuggestion.objects.create(
            family=family, message="Kids pottery class in Lusail please."
        )
        assert suggestion.status == SuggestionStatus.NEW

    def test_category_and_neighborhood_default_blank(self):
        family = make_user("fam_sug2@test.com")
        suggestion = ServiceSuggestion.objects.create(family=family, message="Something.")
        assert suggestion.category == ""
        assert suggestion.neighborhood == ""

    def test_admin_notes_default_blank(self):
        family = make_user("fam_sug3@test.com")
        suggestion = ServiceSuggestion.objects.create(family=family, message="Something.")
        assert suggestion.admin_notes == ""

    def test_str_contains_family_id_and_message_preview(self):
        family = make_user("fam_sug4@test.com")
        suggestion = ServiceSuggestion.objects.create(
            family=family, message="Kids pottery class."
        )
        result = str(suggestion)
        assert str(family.id) in result
        assert "Kids pottery class" in result

    def test_suggestion_status_choices(self):
        choices = [c[0] for c in SuggestionStatus.choices]
        assert "NEW" in choices
        assert "REVIEWED" in choices
        assert "ACTED_ON" in choices
        assert "DISMISSED" in choices

    def test_category_choices_from_listing_category(self):
        family = make_user("fam_sug5@test.com")
        suggestion = ServiceSuggestion.objects.create(
            family=family,
            category=ListingCategory.MASTERCLASSES,
            message="Pottery class.",
        )
        assert suggestion.category == ListingCategory.MASTERCLASSES

    def test_ordering_most_recent_first(self):
        family = make_user("fam_sug6@test.com")
        s1 = ServiceSuggestion.objects.create(family=family, message="First")
        s2 = ServiceSuggestion.objects.create(family=family, message="Second")
        subs = list(ServiceSuggestion.objects.filter(family=family))
        assert subs[0].id == s2.id
        assert subs[1].id == s1.id
