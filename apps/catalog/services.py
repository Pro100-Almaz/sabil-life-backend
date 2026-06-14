"""
Catalog services — distance annotation using pure ORM haversine.

Approach: pure ORM ExpressionWrapper with database trig functions (RADIANS,
SIN, COS, ASIN, SQRT, POWER).  Works on any Postgres version without
extensions (PostGIS is not required), keeping deployment simple.

The haversine formula:
  a = sin²((lat2-lat1)/2) + cos(lat1)*cos(lat2)*sin²((lng2-lng1)/2)
  d = 2 * R * asin(sqrt(a))         R = 6371 km

Implementation note on dlat/dlng:
  We convert all angles to radians first using the DB RADIANS() function.
  The differences are computed on the already-radians values:
    lat1_r = RADIANS(ref_lat)   -- constant scalar
    lat2_r = RADIANS("lat")     -- per-row
    dlat   = lat2_r - lat1_r    -- difference in radians (NOT wrapped in RADIANS again)
  This is the key mistake to avoid: applying RADIANS() to a radians difference
  would scale by π/180 a second time, producing a near-zero (and wrong) result.
"""

import math

from django.db.models import ExpressionWrapper, FloatField, Func, QuerySet, Value


class _Radians(Func):
    """RADIANS(expr) — convert degrees to radians."""

    function = "RADIANS"
    output_field = FloatField()


class _Sin(Func):
    function = "SIN"
    output_field = FloatField()


class _Cos(Func):
    function = "COS"
    output_field = FloatField()


class _Asin(Func):
    function = "ASIN"
    output_field = FloatField()


class _Sqrt(Func):
    function = "SQRT"
    output_field = FloatField()


class _Power(Func):
    """POWER(base, exponent)."""

    function = "POWER"
    output_field = FloatField()


def annotate_distance_km(qs: QuerySet, lat: float, lng: float) -> QuerySet:
    """
    Annotate each listing with ``distance_km`` to (lat, lng) using haversine.
    Listings with null lat/lng get distance NULL.

    The annotation is used by the view for:
    - ``?sort=distance`` ordering (ORDER BY distance_km ASC NULLS LAST)
    - ``?max_distance_km=N`` radius filtering
    """
    R = 6371.0

    # Reference point in radians (scalar constants)
    lat1_r = Value(math.radians(lat), output_field=FloatField())
    lng1_r = Value(math.radians(lng), output_field=FloatField())

    # Per-row lat/lng converted to radians
    lat2_r = _Radians("lat")  # RADIANS("lat")
    lng2_r = _Radians("lng")  # RADIANS("lng")

    # Differences in radians — do NOT wrap in RADIANS again
    dlat = ExpressionWrapper(lat2_r - lat1_r, output_field=FloatField())
    dlng = ExpressionWrapper(lng2_r - lng1_r, output_field=FloatField())

    # sin(dlat / 2)
    sin_dlat_half = _Sin(ExpressionWrapper(dlat / Value(2.0), output_field=FloatField()))
    # sin(dlng / 2)
    sin_dlng_half = _Sin(ExpressionWrapper(dlng / Value(2.0), output_field=FloatField()))

    # sin²(dlat/2)
    sin2_dlat = _Power(sin_dlat_half, Value(2))
    # sin²(dlng/2)
    sin2_dlng = _Power(sin_dlng_half, Value(2))

    # cos(lat1) * cos(lat2)
    cos_product = ExpressionWrapper(
        _Cos(lat1_r) * _Cos(lat2_r),
        output_field=FloatField(),
    )

    # a = sin²(Δlat/2) + cos(lat1)*cos(lat2)*sin²(Δlng/2)
    a = ExpressionWrapper(
        sin2_dlat
        + ExpressionWrapper(
            cos_product * sin2_dlng,
            output_field=FloatField(),
        ),
        output_field=FloatField(),
    )

    # d = 2 * R * asin(sqrt(a))
    distance_expr = ExpressionWrapper(
        Value(2.0 * R) * _Asin(_Sqrt(a)),
        output_field=FloatField(),
    )

    return qs.annotate(distance_km=distance_expr)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Pure-Python haversine for unit tests (spot-checks against the ORM annotation).
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))
