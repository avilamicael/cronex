from django.urls import path
from .views import dashboard_view, definir_filial_padrao

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('definir-filial/', definir_filial_padrao, name='definir_filial_padrao'),


]
