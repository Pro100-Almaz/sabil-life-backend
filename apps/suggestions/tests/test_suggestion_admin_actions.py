"""
Tests for admin bulk actions on ServiceSuggestion.

Covers:
- mark_reviewed, mark_acted_on, mark_dismissed bulk actions transition status.
- admin_notes editable via admin (not via API).
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.suggestions.admin import (
    ServiceSuggestionAdmin,
    mark_acted_on,
    mark_dismissed,
    mark_reviewed,
)
from apps.suggestions.models import ServiceSuggestion, SuggestionStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def make_suggestion(family, message="Test", status_val=SuggestionStatus.NEW):
    return ServiceSuggestion.objects.create(
        family=family, message=message, status=status_val
    )


@pytest.mark.django_db
class TestSuggestionAdminActions:
    def setup_method(self):
        self.site = AdminSite()
        self.admin = ServiceSuggestionAdmin(ServiceSuggestion, self.site)
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            email="superadmin_sug@test.com", password="pass1234!"
        )

    def _request(self):
        from django.contrib.messages.storage.fallback import FallbackStorage

        req = self.factory.get("/")
        req.user = self.superuser
        req.session = {}
        req._messages = FallbackStorage(req)
        return req

    def test_mark_reviewed_transitions_new_to_reviewed(self):
        family = make_user("fam_adm1@test.com")
        s = make_suggestion(family, status_val=SuggestionStatus.NEW)
        qs = ServiceSuggestion.objects.filter(id=s.id)
        req = self._request()
        mark_reviewed(self.admin, req, qs)
        s.refresh_from_db()
        assert s.status == SuggestionStatus.REVIEWED

    def test_mark_acted_on_transitions_to_acted_on(self):
        family = make_user("fam_adm2@test.com")
        s = make_suggestion(family, status_val=SuggestionStatus.REVIEWED)
        qs = ServiceSuggestion.objects.filter(id=s.id)
        req = self._request()
        mark_acted_on(self.admin, req, qs)
        s.refresh_from_db()
        assert s.status == SuggestionStatus.ACTED_ON

    def test_mark_dismissed_transitions_to_dismissed(self):
        family = make_user("fam_adm3@test.com")
        s = make_suggestion(family, status_val=SuggestionStatus.NEW)
        qs = ServiceSuggestion.objects.filter(id=s.id)
        req = self._request()
        mark_dismissed(self.admin, req, qs)
        s.refresh_from_db()
        assert s.status == SuggestionStatus.DISMISSED

    def test_bulk_mark_reviewed_multiple_suggestions(self):
        family = make_user("fam_adm4@test.com")
        s1 = make_suggestion(family, status_val=SuggestionStatus.NEW)
        s2 = make_suggestion(family, status_val=SuggestionStatus.NEW)
        qs = ServiceSuggestion.objects.filter(id__in=[s1.id, s2.id])
        req = self._request()
        mark_reviewed(self.admin, req, qs)
        for s in [s1, s2]:
            s.refresh_from_db()
            assert s.status == SuggestionStatus.REVIEWED

    def test_admin_notes_editable_via_model(self):
        """admin_notes can be set on the model directly (admin form)."""
        family = make_user("fam_adm5@test.com")
        s = make_suggestion(family)
        s.admin_notes = "This was acted on — sourced pottery class."
        s.save()
        s.refresh_from_db()
        assert s.admin_notes == "This was acted on — sourced pottery class."

    def test_admin_notes_not_exposed_via_api(self):
        """admin_notes must never appear in family API responses."""
        from django.urls import reverse
        from rest_framework.test import APIClient

        family = make_user("fam_adm6@test.com")
        s = ServiceSuggestion.objects.create(
            family=family,
            message="Test.",
            admin_notes="Secret internal note.",
        )
        client = APIClient()
        client.force_authenticate(user=family)
        url = reverse("v1:suggestions:suggestions-detail", kwargs={"id": s.id})
        resp = client.get(url)
        assert resp.status_code == 200
        assert "admin_notes" not in resp.data
