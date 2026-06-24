import django_filters
from django.db.models import Q, QuerySet

from apps.catalog.models import Listing


class ListingFilter(django_filters.FilterSet):
    """
    FilterSet for the public Listing list endpoint.

    Filters:
    - category   exact match on ListingCategory; input is uppercased so
                 ?category=tutoring and ?category=TUTORING both work.
    - q          free-text search over title and subtitle (OR, icontains).
    - price_max  listings with price_from_qar <= value.
    - age        listings whose age_groups JSON list contains the given string.
                 Postgres JSONField supports __contains=[value] for array membership.
    - max_distance_km / lat / lng  — these params are declared here so
                 django-filter does not raise "unknown field" errors; the actual
                 distance annotation + filtering is performed in the view after
                 the queryset is annotated (because we need lat/lng to annotate
                 first, and FilterSet runs before the view has a chance to annotate).
    """

    category = django_filters.CharFilter(method="filter_category")
    q = django_filters.CharFilter(method="filter_q")
    price_max = django_filters.NumberFilter(
        field_name="price_from_qar", lookup_expr="lte"
    )
    age = django_filters.CharFilter(method="filter_age")

    # Declared so they are accepted without error; distance logic is in the view.
    max_distance_km = django_filters.NumberFilter(method="noop")
    lat = django_filters.NumberFilter(method="noop")
    lng = django_filters.NumberFilter(method="noop")

    class Meta:
        model = Listing
        fields: list[str] = []

    # ------------------------------------------------------------------
    # Custom filter methods
    # ------------------------------------------------------------------

    def filter_category(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Case-insensitive category exact match."""
        return queryset.filter(category=value.upper())

    def filter_q(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Full-text search: title OR subtitle icontains."""
        return queryset.filter(Q(title__icontains=value) | Q(subtitle__icontains=value))

    def filter_age(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Match listings whose age_groups JSON list contains the given string."""
        return queryset.filter(age_groups__contains=[value])

    def noop(self, queryset: QuerySet, name: str, value: object) -> QuerySet:
        """Placeholder — param accepted but handled outside this FilterSet."""
        return queryset
