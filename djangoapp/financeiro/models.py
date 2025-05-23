from django.db import models
from django.conf import settings
from accounts.models import Empresa
import re

class Filial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        if self.cnpj:
            self.cnpj = re.sub(r'\D', '', self.cnpj)  # Remove tudo que não for número
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome}"

    class Meta:
        verbose_name = 'Filial'
        verbose_name_plural = 'Filiais'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

class Fornecedor(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        if self.cnpj:
            self.cnpj = re.sub(r'\D', '', self.cnpj)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

class Transacao(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

class TipoPagamento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        if self.nome:
            self.nome = self.nome.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Tipo de Pagamento'
        verbose_name_plural = 'Tipos de Pagamento'
        ordering = ['nome']
        unique_together = ('empresa', 'nome')

class ContaPagar(models.Model):
    STATUS_CHOICES = [
        ('a_vencer', 'À Vencer'),
        ('pago', 'Pago'),
        ('vencida', 'Vencida'),
        ('cancelado', 'Cancelado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT)
    transacao = models.ForeignKey(Transacao, on_delete=models.PROTECT)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, null=True, blank=True)
    tipo_pagamento = models.ForeignKey(TipoPagamento, on_delete=models.PROTECT)

    documento = models.CharField(max_length=255)  # obrigatório
    descricao = models.TextField(blank=True)  # opcional
    numero_notas = models.CharField(
        max_length=255, blank=True,
        help_text="Separar por vírgulas se houver mais de uma nota"
    )
    codigo_barras = models.CharField(max_length=255, blank=True)  # opcional

    data_movimentacao = models.DateField()
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(blank=True, null=True)

    valor_bruto = models.DecimalField(max_digits=10, decimal_places=2)
    valor_juros = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_multa = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    outros_acrescimos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valor_saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='a_vencer')
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_vencimento']
        verbose_name = 'Conta a Pagar'
        verbose_name_plural = 'Contas a Pagar'

    def __str__(self):
        return f"{self.transacao} - R$ {self.valor_bruto} - {self.data_vencimento}"

    def calcular_saldo(self):
        self.valor_saldo = (
            self.valor_bruto + self.valor_juros + self.valor_multa + self.outros_acrescimos
            - self.valor_desconto - self.valor_pago
        )
    def save(self, *args, **kwargs):
        # Chama o método para calcular o saldo antes de salvar
        if self.documento:
            self.documento = self.documento.upper()
        if self.descricao:
            self.descricao = self.descricao.upper()

        self.calcular_saldo()
        super().save(*args, **kwargs)

    def marcar_como_pago(self):
        self.valor_pago = (
            self.valor_bruto
            + self.valor_juros
            + self.valor_multa
            + self.outros_acrescimos
            - self.valor_desconto
        )
        self.status = "pago"
        self.save()
        # Atualiza o status para "pago" e salva a conta

