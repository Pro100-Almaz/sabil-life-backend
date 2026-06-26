from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.inquiries.urls import tutor_urlpatterns as inquiry_tutor_urls
from apps.subscriptions.urls import provider_urlpatterns as subscription_provider_urls

urlpatterns = [
    path("admin-panel/", admin.site.urls, name="admin"),
    path(
        "api/v1/",
        include(
            (
                [
                    path("auth/", include("apps.users.urls")),
                    path("core/", include("apps.core.urls")),
                    path("", include("apps.catalog.urls")),
                    path("provider/", include("apps.providers.urls")),
                    path(
                        "tutor/",
                        include((inquiry_tutor_urls, "tutor-inquiries")),
                    ),
                    path(
                        "provider/",
                        include((subscription_provider_urls, "provider-subscriptions")),
                    ),
                    path("", include("apps.inquiries.urls")),
                    path("", include("apps.subscriptions.urls")),
                    path("", include("apps.suggestions.urls")),
                    path("", include("apps.reviews.urls")),
                    path("", include("apps.favorites.urls")),
                ],
                "v1",
            ),
            namespace="v1",
        ),
    ),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/schema/swagger-ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path("__debug__/", include(debug_toolbar.urls)),
    ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
