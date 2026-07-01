import uuid

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.providers.models import (
    ProviderChoices,
    ProviderVerification,
    StatusChoices,
)

User = get_user_model()
CHANGELIST_URL = reverse("admin:providers_providerverification_changelist")


def make_pending_verification() -> ProviderVerification:
    user = User.objects.create_user(
        email=f"applicant_{uuid.uuid4().hex[:8]}@example.com",
        password="TestPass123!",
    )
    return ProviderVerification.objects.create(
        user=user,
        provider_type=ProviderChoices.TUTOR,
        status=StatusChoices.PENDING,
    )


# Unfold's base template hashes static assets via the manifest storage, which
# isn't collected during tests; use plain static storage so admin pages render.
@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class RejectProviderRequestAdminActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            email="reviewer@example.com", password="adminpass"
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_first_click_renders_intermediate_page(self):
        verification = make_pending_verification()
        response = self.client.post(
            CHANGELIST_URL,
            {
                "action": "reject_provider_request",
                ACTION_CHECKBOX_NAME: [verification.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Message to the applicant")
        # Nothing rejected yet — still pending.
        verification.refresh_from_db()
        self.assertEqual(verification.status, StatusChoices.PENDING)

    def test_submitting_message_rejects_and_stores_comment(self):
        verification = make_pending_verification()
        response = self.client.post(
            CHANGELIST_URL,
            {
                "action": "reject_provider_request",
                "apply": "1",
                "comment": "Your credentials could not be verified.",
                ACTION_CHECKBOX_NAME: [verification.pk],
            },
        )
        self.assertEqual(response.status_code, 302)  # redirect back to changelist
        verification.refresh_from_db()
        self.assertEqual(verification.status, StatusChoices.REJECTED)
        self.assertEqual(
            verification.comment, "Your credentials could not be verified."
        )

    def test_blank_message_is_rejected_and_nothing_changes(self):
        verification = make_pending_verification()
        response = self.client.post(
            CHANGELIST_URL,
            {
                "action": "reject_provider_request",
                "apply": "1",
                "comment": "   ",
                ACTION_CHECKBOX_NAME: [verification.pk],
            },
        )
        # Re-renders the form (200), does not redirect.
        self.assertEqual(response.status_code, 200)
        verification.refresh_from_db()
        self.assertEqual(verification.status, StatusChoices.PENDING)
        self.assertEqual(verification.comment, "")

    def test_one_message_applies_to_all_selected(self):
        v1 = make_pending_verification()
        v2 = make_pending_verification()
        self.client.post(
            CHANGELIST_URL,
            {
                "action": "reject_provider_request",
                "apply": "1",
                "comment": "Applications are paused this cycle.",
                ACTION_CHECKBOX_NAME: [v1.pk, v2.pk],
            },
        )
        for v in (v1, v2):
            v.refresh_from_db()
            self.assertEqual(v.status, StatusChoices.REJECTED)
            self.assertEqual(v.comment, "Applications are paused this cycle.")
