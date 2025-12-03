from django.urls import path
from . import views
from financeiro.contas.incluir_contas import generic_autocomplete, baixar_contas_pagar_bulk
from financeiro.nfe import views as nfe_views

urlpatterns = [
    path('contas/lancar/', views.lancar_conta_pagar, name='lancar_conta_pagar'),
    path('contas/listar/', views.listar_contas_pagar, name='listar_contas_pagar'),
    path('contas/baixar/', baixar_contas_pagar_bulk, name='baixar_contas_pagar_bulk'),
    path('contas/importar-arquivo/', views.importar_contas_arquivo, name='importar_contas_arquivo'),

    path('autocomplete/<str:model_name>/', generic_autocomplete, name='generic_autocomplete'),

    path('concilia-contas/', views.concilia_contas_view, name='concilia_contas'),
    # path('concilia-contas/validar/', views.validar_ofx, name='validar_ofx'),
    path('concilia/incluir/', views.incluir_conta_conciliacao, name='incluir_conta_conciliacao'),

    path('relatorio-faturamento/<int:relatorio_id>/download/', views.download_relatorio_faturamento, name='download_relatorio_faturamento'),

    # ========== NOTAS FISCAIS ELETRÔNICAS ==========
    # Certificados Digitais
    path('certificados/', nfe_views.certificados_lista, name='certificados_lista'),
    path('certificados/adicionar/', nfe_views.certificado_adicionar, name='certificado_adicionar'),
    path('certificados/<int:pk>/editar/', nfe_views.certificado_editar, name='certificado_editar'),
    path('certificados/<int:pk>/resetar-nsu/', nfe_views.certificado_resetar_nsu, name='certificado_resetar_nsu'),
    path('certificados/<int:pk>/sincronizar-nsu/', nfe_views.certificado_sincronizar_nsu, name='certificado_sincronizar_nsu'),
    path('certificados/<int:pk>/deletar/', nfe_views.certificado_deletar, name='certificado_deletar'),

    # Consulta e gestão de NF-e
    path('nfe/consultar/', nfe_views.nfe_consultar, name='nfe_consultar'),
    path('nfe/lista/', nfe_views.nfe_lista, name='nfe_lista'),
    path('nfe/<int:pk>/', nfe_views.nfe_detalhes, name='nfe_detalhes'),
    path('nfe/<int:pk>/deletar/', nfe_views.nfe_deletar, name='nfe_deletar'),

    # Download de XMLs
    path('nfe/<int:pk>/download/', nfe_views.nfe_download_xml, name='nfe_download_xml'),
    path('nfe/download-massa/', nfe_views.nfe_download_massa, name='nfe_download_massa'),

    # Monitoramento e configuração de importações automáticas
    path('nfe/status/', nfe_views.nfe_status_importacao, name='nfe_status_importacao'),
    path('nfe/config/<int:config_id>/toggle/', nfe_views.nfe_ativar_busca_automatica, name='nfe_ativar_busca_automatica'),
    path('nfe/config/criar/<int:certificado_id>/', nfe_views.nfe_criar_configuracao, name='nfe_criar_configuracao'),

]