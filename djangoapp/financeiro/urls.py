from django.urls import path
from . import views
from financeiro.contas.incluir_contas import generic_autocomplete

urlpatterns = [
    path('contas/lancar/', views.lancar_conta_pagar, name='lancar_conta_pagar'),
    path('autocomplete/<str:model_name>/', generic_autocomplete, name='generic_autocomplete'),

]