# tarefas/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_tarefas, name='listar_tarefas'),
    path('nova/', views.criar_tarefa, name='criar_tarefa'),
    path('finalizar/<int:tarefa_id>/', views.finalizar_tarefa, name='finalizar_tarefa'),
    path('validar/<int:tarefa_id>/', views.validar_tarefa, name='validar_tarefa'),
    path('rejeitar/<int:tarefa_id>/', views.rejeitar_tarefa, name='rejeitar_tarefa'),
    path('historico/<int:tarefa_id>/', views.historico_tarefa, name='historico_tarefa'),
    path('rejeitar-execucao/<int:tarefa_id>/', views.rejeitar_execucao, name='rejeitar_execucao'),
    path('validar-execucao/<int:tarefa_id>/', views.validar_execucao, name='validar_execucao'),
    path('marcar-visualizado/<int:tarefa_id>/', views.marcar_tarefa_visualizada, name='marcar_visualizado'),

    
]
