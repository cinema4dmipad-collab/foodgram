from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from recipes.views import redirect_to_recipe

urlpatterns = [
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
    path('s/<str:code>/', redirect_to_recipe, name='redirect_to_recipe'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )

urlpatterns += [
    re_path(r'^(?!api/|admin/|s/).*', TemplateView.as_view(
        template_name='index.html'
    )),
]
