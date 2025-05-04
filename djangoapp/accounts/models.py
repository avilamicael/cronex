from django.contrib.auth.models import AbstractUser
from django.db import models

class Empresa(models.Model):
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, unique=True)
    endereco = models.TextField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    responsavel = models.CharField(max_length=255, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    trial = models.BooleanField(default=False)
    trial_expira_em = models.DateField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome
    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nome']
        # Adiciona a opção de ordenação por nome na interface de administração


class User(AbstractUser):
    email = models.EmailField(unique=True)
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    nivel_acesso = models.CharField(
        max_length=50,
        choices=[
            ('admin', 'Administrador'),
            ('gerente', 'Gerente'),
            ('colaborador', 'Colaborador'),
        ],
        default='colaborador'
    )
    ativo = models.BooleanField(default=True)

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.username} - {self.empresa.nome}"
