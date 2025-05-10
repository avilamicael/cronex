# tarefas/admin.py
from django.contrib import admin
from .models import Tarefa, HistoricoTarefa


class HistoricoInline(admin.TabularInline):
    model = HistoricoTarefa
    extra = 0
    readonly_fields = ('usuario', 'acao', 'data', 'observacao')
    can_delete = False


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'empresa', 'responsavel', 'status', 'data_execucao', 'data_finalizacao', 'data_validacao')
    list_filter = ('status', 'empresa', 'data_execucao')
    search_fields = ('titulo', 'descricao', 'responsavel__first_name', 'responsavel__last_name')
    date_hierarchy = 'data_execucao'
    readonly_fields = ('data_criacao', 'data_finalizacao', 'data_validacao')
    inlines = [HistoricoInline]

@admin.register(HistoricoTarefa)
class HistoricoTarefaAdmin(admin.ModelAdmin):
    list_display = ('tarefa', 'acao', 'usuario', 'data')
    search_fields = ('tarefa__titulo', 'usuario__username', 'acao')
    list_filter = ('acao', 'data')
