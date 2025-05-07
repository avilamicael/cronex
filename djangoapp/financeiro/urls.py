from django.urls import path
from . import views
from financeiro.contas.incluir_contas import generic_autocomplete, baixar_contas_pagar_bulk

urlpatterns = [
    path('contas/lancar/', views.lancar_conta_pagar, name='lancar_conta_pagar'),
    path('contas/listar/', views.listar_contas_pagar, name='listar_contas_pagar'),
    path('contas/baixar/', baixar_contas_pagar_bulk, name='baixar_contas_pagar_bulk'),
    path('contas/importar-arquivo/', views.importar_contas_arquivo, name='importar_contas_arquivo'),

    path('autocomplete/<str:model_name>/', generic_autocomplete, name='generic_autocomplete'),

]