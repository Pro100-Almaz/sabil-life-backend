import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.providers.models import TutorDetail
from apps.reviews.admin import ReviewAdmin
from apps.reviews.models import (
    Review,
    ReviewReport,
    TutorReview,
    TutorReviewReport,
)

User = get_user_model()


def _user(email):
    return User.objects.create_user(email=email, password="pass1234!")


@pytest.mark.django_db
class TestReviewReports:
    def setup_method(self):
        self.client = APIClient()
        self.author = _user("report-author@test.com")
        self.reporter = _user("reporter@test.com")
        self.listing = Listing.objects.create(
            title="Reported listing",
            category=ListingCategory.SCHOOLS,
            status=ListingStatus.ACTIVE,
        )
        self.review = Review.objects.create(
            listing=self.listing,
            author=self.author,
            rating=1,
            text="Inappropriate content",
        )
        self.url = reverse("v1:review-report", kwargs={"review_id": self.review.id})

    def test_authentication_is_required(self):
        response = self.client.post(self.url)

        assert response.status_code == 401

    def test_user_can_report_once_and_repeat_is_idempotent(self):
        self.client.force_authenticate(self.reporter)

        first = self.client.post(self.url)
        second = self.client.post(self.url)

        assert first.status_code == 201
        assert second.status_code == 200
        assert second.json()["report_count"] == 1
        assert ReviewReport.objects.filter(review=self.review).count() == 1

    def test_author_can_report_own_review(self):
        self.client.force_authenticate(self.author)

        response = self.client.post(self.url)

        assert response.status_code == 201
        assert ReviewReport.objects.filter(
            review=self.review,
            reporter=self.author,
        ).exists()

    def test_admin_orders_reviews_by_report_count(self):
        other_author = _user("other-author@test.com")
        priority_review = Review.objects.create(
            listing=self.listing,
            author=other_author,
            rating=2,
        )
        ReviewReport.objects.create(review=priority_review, reporter=self.reporter)
        ReviewReport.objects.create(review=priority_review, reporter=self.author)
        ReviewReport.objects.create(review=self.review, reporter=other_author)

        request = RequestFactory().get("/admin-panel/reviews/review/")
        request.user = User.objects.create_superuser(
            email="review-admin@test.com",
            password="pass1234!",
        )
        queryset = ReviewAdmin(Review, admin.site).get_queryset(request)

        assert list(queryset.values_list("id", flat=True)) == [
            priority_review.id,
            self.review.id,
        ]

    def test_deleting_review_cascades_reports(self):
        ReviewReport.objects.create(review=self.review, reporter=self.reporter)

        self.review.delete()

        assert not ReviewReport.objects.exists()

    def test_tutor_review_can_be_reported_once(self):
        tutor_user = _user("reported-tutor@test.com")
        tutor = TutorDetail.objects.create(user=tutor_user)
        tutor_review = TutorReview.objects.create(
            tutor=tutor,
            author=self.author,
            rating=1,
        )
        url = reverse(
            "v1:tutor-review-report",
            kwargs={"review_id": tutor_review.id},
        )
        self.client.force_authenticate(self.reporter)

        assert self.client.post(url).status_code == 201
        assert self.client.post(url).status_code == 200
        assert TutorReviewReport.objects.filter(review=tutor_review).count() == 1

    def test_author_can_report_own_tutor_review(self):
        tutor_user = _user("self-reported-tutor@test.com")
        tutor = TutorDetail.objects.create(user=tutor_user)
        tutor_review = TutorReview.objects.create(
            tutor=tutor,
            author=self.author,
            rating=1,
        )
        url = reverse(
            "v1:tutor-review-report",
            kwargs={"review_id": tutor_review.id},
        )
        self.client.force_authenticate(self.author)

        assert self.client.post(url).status_code == 201
        assert TutorReviewReport.objects.filter(
            review=tutor_review,
            reporter=self.author,
        ).exists()
