import django_filters
from django.db.models import Q, QuerySet

from apps.catalog.models import Listing
from apps.providers.models import TutorDetail


class BaseFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")

    def filter_search(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        pass

    def noop(self, queryset: QuerySet, name: str, value: object) -> QuerySet:
        """Placeholder — param accepted but handled outside this FilterSet."""
        return queryset


class ListingFilter(BaseFilter):
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
    tags = django_filters.CharFilter(method="filter_tags")

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

    def filter_category(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Case-insensitive category exact match."""
        return queryset.filter(category=value.upper())

    def filter_tags(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        names = [v.strip() for v in value.split(',') if v.strip()]
        
        if not names:
            return queryset
        
        return queryset.filter(tags__name__in=names).distinct()

    def filter_age(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Match listings whose age_groups JSON list contains the given string."""
        return queryset.filter(age_groups__contains=[value])

    def filter_search(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Full-text search: title OR subtitle icontains."""
        return queryset.filter(Q(title__icontains=value) | Q(subtitle__icontains=value))


class TutorFilter(BaseFilter):
    """
    FilterSet for the public tutor list endpoint.

    Filters:
    - search    free-text over user.full_name OR subjects (OR, icontains/contains).
    - formats   one or more formats; ?formats=ONLINE or ?formats=ONLINE,AT_CENTRE.
                Matches tutors whose formats JSON list contains ANY of the values.
    - age_groups one or more age groups; same single/CSV/OR semantics as formats.
    - languages one or more languages; same single/CSV/OR semantics as formats.
    - price_min / price_max  bound price_per_hour_qar; either bound may be given
                alone (open-ended on the missing side).
    - trial_available  boolean (?trial_available=true / false).
    """

    formats = django_filters.CharFilter(method="filter_formats")
    age_groups = django_filters.CharFilter(method="filter_age_groups")
    languages = django_filters.CharFilter(method="filter_languages")
    price_min = django_filters.NumberFilter(
        field_name="price_per_hour_qar", lookup_expr="gte"
    )
    price_max = django_filters.NumberFilter(
        field_name="price_per_hour_qar", lookup_expr="lte"
    )
    trial_available = django_filters.BooleanFilter(field_name="trial_available")
    city = django_filters.CharFilter(field_name="city")

    class Meta:
        model = TutorDetail
        fields: list[str] = []

    @staticmethod
    def _split(value: str) -> list[str]:
        """Split a comma-separated param into a clean list of values."""
        return [v.strip() for v in value.split(",") if v.strip()]

    def _filter_json_any(
        self, queryset: QuerySet, field: str, value: str
    ) -> QuerySet:
        """Match rows whose JSON list `field` contains ANY of the given values."""
        values = self._split(value)
        if not values:
            return queryset
        q = Q()
        for v in values:
            q |= Q(**{f"{field}__contains": [v]})
        return queryset.filter(q)

    def filter_search(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Full-text search: full_name OR subjects contains."""
        return queryset.filter(
            Q(user__full_name__icontains=value)
            | Q(subjects__contains=[value.capitalize()])
        )

    def filter_formats(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter by one or more formats: ONLINE, ONE_ON_ONE, AT_CENTRE etc."""
        return self._filter_json_any(queryset, "formats", value)

    def filter_age_groups(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter by one or more age groups, e.g. 6-11, 12-15."""
        return self._filter_json_any(queryset, "age_groups", value)

    def filter_languages(self, queryset: QuerySet, name: str, value: str) -> QuerySet:
        """Filter by one or more languages, e.g. EN, AR."""
        return self._filter_json_any(queryset, "languages", value)
