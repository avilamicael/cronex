from django.urls import path
from .views import definir_filial_padrao

urlpatterns = [
    path('definir-filial/', definir_filial_padrao, name='definir_filial_padrao'),


]
