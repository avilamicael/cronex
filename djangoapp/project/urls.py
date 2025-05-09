from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.views.generic import RedirectView
from core.views import dashboard_view

urlpatterns = [
    path('acesso_restrito/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # login, logout
    path('accounts/', include('accounts.urls')),
    path('', include('core.urls')),  # Inclui URLs do app core
    path('financeiro/', include('financeiro.urls')),  # Inclui URLs do app financeiro

    path('', dashboard_view, name='dashboard'), # Redireciona para a view de dashboard

]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
