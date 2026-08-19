import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from knox.models import AuthToken
from rest_framework.test import APIClient, APITestCase

from apps.providers.models import (
    ProviderChoices,
    ProviderVerification,
    StatusChoices,
    TutorDetail,
)
from apps.users.enums import UserRole
from apps.users.models import CustomUser

TUTOR_DETAIL_URL = "/api/v1/provider/tutor-detail/"
VERIFY_URL = "/api/v1/provider/verify/"
# Cancellation is a DELETE on the per-provider-type verify URL.
CANCEL_URL = "/api/v1/provider/verify/TUTOR/"
ADMIN_URL = "/api/v1/provider/verify/admin/"


def make_user(
    role: str = UserRole.FAMILY,
    verified: bool = True,
    email: str | None = None,
) -> CustomUser:
    email = email or f"{role.lower()}_{uuid.uuid4().hex[:8]}@example.com"
    return CustomUser.objects.create_user(
        email=email,
        password="TestPass123!",
        role=role,
        is_verified=verified,
    )


def auth_client(user: CustomUser) -> APIClient:
    client = APIClient()
    _, token = AuthToken.objects.create(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def masterclass_payload() -> dict:
    return {
        "provider_type": ProviderChoices.MASTERCLASS,
        "ai_processing_consent": True,
        "cv": SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.4\n% test PDF",
            content_type="application/pdf",
        ),
    }


class VerificationLifecycleFromTutorDetailTests(APITestCase):
    def setUp(self):
        self.user = make_user(role=UserRole.TUTOR)
        self.client = auth_client(self.user)

    def _verification(self) -> ProviderVerification:
        return ProviderVerification.objects.get(
            user=self.user, provider_type=ProviderChoices.TUTOR
        )

    def test_creating_tutor_detail_creates_pending_verification(self):
        self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")
        verification = self._verification()
        self.assertEqual(verification.status, StatusChoices.PENDING)
        self.assertEqual(verification.provider_type, ProviderChoices.TUTOR)

    def test_updating_tutor_detail_sets_status_updated(self):
        self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")
        self.client.patch(TUTOR_DETAIL_URL, {"bio": "Updated"}, format="json")
        self.assertEqual(self._verification().status, StatusChoices.UPDATED)

    def test_resubmitting_clears_previous_rejection_comment(self):
        self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")
        verification = self._verification()
        verification.status = StatusChoices.REJECTED
        verification.comment = "Missing credentials"
        verification.save()

        self.client.patch(TUTOR_DETAIL_URL, {"bio": "Now with creds"}, format="json")
        verification.refresh_from_db()
        self.assertEqual(verification.status, StatusChoices.UPDATED)
        self.assertEqual(verification.comment, "")

    def test_only_one_verification_per_user_and_type(self):
        self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")
        self.client.patch(TUTOR_DETAIL_URL, {"bio": "Edit"}, format="json")
        self.assertEqual(ProviderVerification.objects.filter(user=self.user).count(), 1)

    def test_linkedin_url_is_optional(self):
        response = self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["linkedin_url"], "")

    def test_accepts_linkedin_url(self):
        linkedin_url = "https://www.linkedin.com/in/example-tutor/"
        response = self.client.post(
            TUTOR_DETAIL_URL,
            {"bio": "Hello", "linkedin_url": linkedin_url},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["linkedin_url"], linkedin_url)

        public_response = APIClient().get("/api/v1/tutors/")
        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(public_response.data["results"][0]["linkedin_url"], linkedin_url)

    def test_rejects_non_url_linkedin_value(self):
        response = self.client.post(
            TUTOR_DETAIL_URL,
            {"linkedin_url": "this is not a link"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("linkedin_url", response.data)

    def test_rejects_non_linkedin_url(self):
        response = self.client.post(
            TUTOR_DETAIL_URL,
            {"linkedin_url": "https://example.com/in/example-tutor"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("linkedin_url", response.data)


class MasterclassCvVerificationTests(APITestCase):
    def setUp(self):
        self.user = make_user(role=UserRole.FAMILY)
        self.client = auth_client(self.user)

    def test_masterclass_request_requires_cv(self):
        response = self.client.post(
            VERIFY_URL,
            {
                "provider_type": ProviderChoices.MASTERCLASS,
                "ai_processing_consent": True,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cv", response.data)

    def test_masterclass_request_accepts_pdf_cv(self):
        cv = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.4\n% test PDF",
            content_type="application/pdf",
        )
        response = self.client.post(
            VERIFY_URL,
            {
                "provider_type": ProviderChoices.MASTERCLASS,
                "cv": cv,
                "ai_processing_consent": True,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        verification = ProviderVerification.objects.get(user=self.user)
        self.assertTrue(verification.cv.name.endswith(".pdf"))
        self.assertTrue(response.data["has_cv"])

    def test_masterclass_request_requires_ai_processing_consent(self):
        cv = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.4\n% test PDF",
            content_type="application/pdf",
        )
        response = self.client.post(
            VERIFY_URL,
            {"provider_type": ProviderChoices.MASTERCLASS, "cv": cv},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("ai_processing_consent", response.data)

    def test_masterclass_request_rejects_non_pdf(self):
        cv = SimpleUploadedFile(
            "resume.txt",
            b"not a PDF",
            content_type="text/plain",
        )
        response = self.client.post(
            VERIFY_URL,
            {
                "provider_type": ProviderChoices.MASTERCLASS,
                "cv": cv,
                "ai_processing_consent": True,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cv", response.data)


class ProviderVerificationReadTests(APITestCase):
    def setUp(self):
        self.user = make_user(role=UserRole.TUTOR)
        self.client = auth_client(self.user)
        self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")

    def test_provider_can_list_own_verification(self):
        resp = self.client.get(VERIFY_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["status"], StatusChoices.PENDING)

    def test_rejection_reason_is_visible_to_provider(self):
        verification = ProviderVerification.objects.get(user=self.user)
        verification.status = StatusChoices.REJECTED
        verification.comment = "Blurry documents"
        verification.save()

        resp = self.client.get(VERIFY_URL)
        self.assertEqual(resp.data[0]["status"], StatusChoices.REJECTED)
        self.assertEqual(resp.data[0]["comment"], "Blurry documents")

    def test_anonymous_cannot_list(self):
        resp = APIClient().get(VERIFY_URL)
        self.assertEqual(resp.status_code, 401)

    def test_family_can_list_but_sees_nothing(self):
        # The role is granted on approval, so a not-yet-provider user may
        # still call the endpoint — they just have no records yet.
        client = auth_client(make_user(role=UserRole.FAMILY))
        resp = client.get(VERIFY_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [])


class RequestVerificationTests(APITestCase):
    def test_user_can_request_verification(self):
        # A plain FAMILY user (no provider role yet) can request — the role
        # is only granted once an admin approves.
        user = make_user(role=UserRole.FAMILY)
        client = auth_client(user)
        resp = client.post(VERIFY_URL, masterclass_payload(), format="multipart")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], StatusChoices.PENDING)
        self.assertEqual(resp.data["provider_type"], "MASTERCLASS")
        self.assertTrue(
            ProviderVerification.objects.filter(
                user=user, provider_type=ProviderChoices.MASTERCLASS
            ).exists()
        )

    def test_request_does_not_grant_role(self):
        user = make_user(role=UserRole.FAMILY)
        auth_client(user).post(VERIFY_URL, masterclass_payload(), format="multipart")
        if hasattr(user, "_role_names_cache"):
            del user._role_names_cache
        self.assertFalse(user.has_role(UserRole.MASTERCLASS))

    def test_unknown_provider_type(self):
        user = make_user(role=UserRole.MASTERCLASS)
        resp = auth_client(user).post(
            VERIFY_URL, {"provider_type": "WIZARD"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_pending_request_conflicts(self):
        user = make_user(role=UserRole.MASTERCLASS)
        client = auth_client(user)
        client.post(VERIFY_URL, masterclass_payload(), format="multipart")
        resp = client.post(VERIFY_URL, masterclass_payload(), format="multipart")
        self.assertEqual(resp.status_code, 409)

    def test_can_rerequest_after_rejection(self):
        user = make_user(role=UserRole.MASTERCLASS)
        client = auth_client(user)
        client.post(VERIFY_URL, masterclass_payload(), format="multipart")
        v = ProviderVerification.objects.get(user=user)
        v.status = StatusChoices.REJECTED
        v.comment = "Need more info"
        v.save()

        resp = client.post(VERIFY_URL, masterclass_payload(), format="multipart")
        self.assertEqual(resp.status_code, 200)
        v.refresh_from_db()
        self.assertEqual(v.status, StatusChoices.UPDATED)
        self.assertEqual(v.comment, "")

    def test_cannot_rerequest_when_approved(self):
        user = make_user(role=UserRole.MASTERCLASS)
        client = auth_client(user)
        client.post(VERIFY_URL, masterclass_payload(), format="multipart")
        v = ProviderVerification.objects.get(user=user)
        v.status = StatusChoices.APPROVED
        v.save()
        resp = client.post(VERIFY_URL, masterclass_payload(), format="multipart")
        self.assertEqual(resp.status_code, 409)


class CancelVerificationTests(APITestCase):
    def setUp(self):
        self.user = make_user(role=UserRole.TUTOR)
        self.client = auth_client(self.user)
        self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")

    def test_provider_can_cancel(self):
        resp = self.client.delete(CANCEL_URL)
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ProviderVerification.objects.filter(user=self.user).exists())

    def test_cannot_cancel_approved(self):
        v = ProviderVerification.objects.get(user=self.user)
        v.status = StatusChoices.APPROVED
        v.save()
        resp = self.client.delete(CANCEL_URL)
        self.assertEqual(resp.status_code, 400)

    def test_cancel_unknown_provider_type(self):
        resp = self.client.delete("/api/v1/provider/verify/WIZARD/")
        self.assertEqual(resp.status_code, 400)

    def test_cancel_without_request_returns_404(self):
        # A fresh user with no tutor detail / verification.
        other = make_user(role=UserRole.FAMILY)
        resp = auth_client(other).delete(CANCEL_URL)
        self.assertEqual(resp.status_code, 404)


class AdminReviewTests(APITestCase):
    def setUp(self):
        self.tutor = make_user(role=UserRole.TUTOR)
        auth_client(self.tutor).post(TUTOR_DETAIL_URL, {"bio": "Hi"}, format="json")
        self.verification = ProviderVerification.objects.get(user=self.tutor)

        self.manager = make_user(role=UserRole.MANAGER)
        self.client = auth_client(self.manager)
        self.detail_url = f"{ADMIN_URL}{self.verification.pk}/"

    def test_manager_can_list(self):
        resp = self.client.get(ADMIN_URL)
        self.assertEqual(resp.status_code, 200)

    def test_list_filter_by_status(self):
        resp = self.client.get(f"{ADMIN_URL}?status=PENDING")
        self.assertEqual(resp.status_code, 200)
        results = resp.data["results"] if "results" in resp.data else resp.data
        self.assertTrue(all(r["status"] == "PENDING" for r in results))

    def test_approve_sets_status_and_verifies_tutor_detail(self):
        resp = self.client.patch(self.detail_url, {"status": "APPROVED"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, StatusChoices.APPROVED)
        self.assertTrue(TutorDetail.objects.get(user=self.tutor).is_verified)

    def test_approve_grants_role(self):
        # A user with no provider role gets it granted on approval.
        user = make_user(role=UserRole.FAMILY)
        auth_client(user).post(VERIFY_URL, masterclass_payload(), format="multipart")
        v = ProviderVerification.objects.get(user=user)
        self.client.patch(f"{ADMIN_URL}{v.pk}/", {"status": "APPROVED"}, format="json")

        user.refresh_from_db()
        if hasattr(user, "_role_names_cache"):
            del user._role_names_cache
        self.assertTrue(user.has_role(UserRole.MASTERCLASS))

    def test_reject_revokes_role(self):
        # An already-approved provider who is later rejected loses the role.
        self.assertTrue(self.tutor.has_role(UserRole.TUTOR))
        self.client.patch(
            self.detail_url,
            {"status": "REJECTED", "comment": "Credentials lapsed"},
            format="json",
        )
        self.tutor.refresh_from_db()
        if hasattr(self.tutor, "_role_names_cache"):
            del self.tutor._role_names_cache
        self.assertFalse(self.tutor.has_role(UserRole.TUTOR))

    def test_reject_requires_comment(self):
        resp = self.client.patch(self.detail_url, {"status": "REJECTED"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("comment", resp.data)

    def test_reject_with_comment(self):
        resp = self.client.patch(
            self.detail_url,
            {"status": "REJECTED", "comment": "Incomplete profile"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, StatusChoices.REJECTED)
        self.assertEqual(self.verification.comment, "Incomplete profile")
        self.assertFalse(TutorDetail.objects.get(user=self.tutor).is_verified)

    def test_cannot_set_arbitrary_status(self):
        resp = self.client.patch(self.detail_url, {"status": "PENDING"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_cannot_review_cancelled(self):
        self.verification.status = StatusChoices.CANCELLED
        self.verification.save()
        resp = self.client.patch(self.detail_url, {"status": "APPROVED"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_family_cannot_access_admin(self):
        client = auth_client(make_user(role=UserRole.FAMILY))
        self.assertEqual(client.get(ADMIN_URL).status_code, 403)
        self.assertEqual(
            client.patch(
                self.detail_url, {"status": "APPROVED"}, format="json"
            ).status_code,
            403,
        )
