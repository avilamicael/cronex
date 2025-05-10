# tarefas/models.py
from django.db import models
from django.utils import timezone
from accounts.models import User, Empresa


class Tarefa(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('executado', 'Executado pelo responsável'),
        ('validado', 'Validado pelo criador'),
        ('rejeitado', 'Rejeitado pelo criador'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    descricao = models.TextField(blank=True)
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tarefas')
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tarefas_criadas')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_execucao = models.DateTimeField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_finalizacao = models.DateTimeField(null=True, blank=True)
    data_validacao = models.DateTimeField(null=True, blank=True)
    data_para_notificar = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.titulo


class HistoricoTarefa(models.Model):
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name='historico')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=255)
    data = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.tarefa.titulo} - {self.acao}"