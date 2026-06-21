from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/', include('api.urls')),
    path('api/', include('djoser.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

urlpatterns += [
    re_path(r'^(?!api/|admin/).*', TemplateView.as_view(
        template_name='index.html'
    )),
]
