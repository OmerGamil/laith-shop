# shopproject/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("summernote/", include("django_summernote.urls")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include(("shop.urls", "shop"), namespace="shop")),  # root handled by shop.urls
)

# Dev static/media
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(getattr(settings, "MEDIA_URL", "/media/"),
                          document_root=getattr(settings, "MEDIA_ROOT", None))
