from django.db import models
from django.conf import settings
from accounts.models import Empresa
import re

class Filial(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    conta_bancaria = models.CharField(max_length=100, blank=True, null=True)

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

    RECORRENCIA_CHOICES = [
        ('semanal', 'Semanal (7 dias)'),
        ('quinzenal', 'Quinzenal (15 dias)'),
        ('mensal', 'Mensal (1 mês)'),
        ('bimestral', 'Bimestral (2 meses)'),
        ('trimestral', 'Trimestral (3 meses)'),
        ('semestral', 'Semestral (6 meses)'),
        ('anual', 'Anual (12 meses)'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    filial = models.ForeignKey(Filial, on_delete=models.PROTECT, related_name='contas_filial')
    transacao = models.ForeignKey(Transacao, on_delete=models.PROTECT)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, null=True, blank=True)
    tipo_pagamento = models.ForeignKey(TipoPagamento, on_delete=models.PROTECT)
    conta_bancaria_pagamento = models.ForeignKey(Filial, on_delete=models.PROTECT, null=True, blank=True, related_name='contas_banco_pagador', verbose_name='Conta Bancária para Pagamento')

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

    # Campos de recorrência
    eh_recorrente = models.BooleanField(default=False, verbose_name='É recorrente?')
    recorrencia_tipo = models.CharField(
        max_length=20,
        choices=RECORRENCIA_CHOICES,
        blank=True,
        null=True,
        verbose_name='Tipo de recorrência'
    )
    recorrencia_grupo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Identificador do grupo de contas recorrentes',
        verbose_name='Grupo de recorrência'
    )
    numero_parcela = models.IntegerField(
        blank=True,
        null=True,
        help_text='Número desta parcela (ex: 1 de 12)',
        verbose_name='Nº da Parcela'
    )
    total_parcelas = models.IntegerField(
        blank=True,
        null=True,
        help_text='Total de parcelas da recorrência',
        verbose_name='Total de Parcelas'
    )

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

from django.core.files.storage import FileSystemStorage
import os

class OverwriteStorage(FileSystemStorage):
    """Storage que sobrescreve arquivo ao invés de adicionar sufixo"""

    def get_available_name(self, name, max_length=None):
        """
        Retorna o nome do arquivo como está, deletando o arquivo existente se houver.
        Isso previne que o Django adicione sufixos como '_abc123' ao nome.
        """
        # Se o arquivo já existe, remove ele
        if self.exists(name):
            os.remove(self.path(name))
        return name

# Cria uma instância global do storage personalizado
relatorio_storage = OverwriteStorage()

class RelatorioFaturamentoMensal(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    mes = models.IntegerField(help_text="Mês de referência (1-12)")
    ano = models.IntegerField(help_text="Ano de referência")
    arquivo_zip = models.FileField(
        upload_to='relatorios_faturamento/%Y/%m/',
        blank=True,
        null=True,
        storage=relatorio_storage
    )
    data_geracao = models.DateTimeField(auto_now_add=True)
    gerado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Relatório de Faturamento Mensal'
        verbose_name_plural = 'Relatórios de Faturamento Mensal'
        ordering = ['-ano', '-mes']
        unique_together = ('empresa', 'mes', 'ano')

    def __str__(self):
        return f"Relatório {self.mes:02d}/{self.ano} - {self.empresa.nome}"

    @property
    def mes_ano_formatado(self):
        meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        return f"{meses[self.mes]}/{self.ano}"

    def delete(self, *args, **kwargs):
        # Remove o arquivo ao deletar o registro
        if self.arquivo_zip:
            self.arquivo_zip.delete(save=False)
        super().delete(*args, **kwargs)


# ==============================
# GESTÃO DE NOTAS FISCAIS ELETRÔNICAS
# ==============================

class CertificadoDigital(models.Model):
    """
    Armazena certificados digitais (A1) para consulta de NF-e na SEFAZ.
    Senhas são criptografadas antes de serem salvas.
    """
    UF_CHOICES = [
        ('11', 'Rondônia'), ('12', 'Acre'), ('13', 'Amazonas'), ('14', 'Roraima'),
        ('15', 'Pará'), ('16', 'Amapá'), ('17', 'Tocantins'), ('21', 'Maranhão'),
        ('22', 'Piauí'), ('23', 'Ceará'), ('24', 'Rio Grande do Norte'),
        ('25', 'Paraíba'), ('26', 'Pernambuco'), ('27', 'Alagoas'), ('28', 'Sergipe'),
        ('29', 'Bahia'), ('31', 'Minas Gerais'), ('32', 'Espírito Santo'),
        ('33', 'Rio de Janeiro'), ('35', 'São Paulo'), ('41', 'Paraná'),
        ('42', 'Santa Catarina'), ('43', 'Rio Grande do Sul'), ('50', 'Mato Grosso do Sul'),
        ('51', 'Mato Grosso'), ('52', 'Goiás'), ('53', 'Distrito Federal'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='certificados')
    filial = models.ForeignKey(
        Filial,
        on_delete=models.CASCADE,
        related_name='certificados',
        help_text='Filial proprietária do certificado (CNPJ)'
    )

    # Dados do certificado
    arquivo_pfx = models.FileField(
        upload_to='certificados/%Y/%m/',
        help_text='Arquivo .pfx ou .p12 do certificado digital A1'
    )
    senha_encrypted = models.BinaryField(
        help_text='Senha do certificado (criptografada automaticamente)'
    )
    uf_codigo = models.CharField(
        max_length=2,
        choices=UF_CHOICES,
        verbose_name='UF',
        help_text='Estado para consulta na SEFAZ'
    )

    # Validade
    data_validade = models.DateField(
        help_text='Data de vencimento do certificado'
    )
    ativo = models.BooleanField(
        default=True,
        help_text='Certificado ativo para uso'
    )

    # Controle
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    # NSU controle
    ultimo_nsu = models.CharField(
        max_length=15,
        default='000000000000000',
        help_text='Último NSU consultado na SEFAZ'
    )

    class Meta:
        verbose_name = 'Certificado Digital'
        verbose_name_plural = 'Certificados Digitais'
        ordering = ['-ativo', 'filial__nome']
        unique_together = ('empresa', 'filial')

    def __str__(self):
        status = "Ativo" if self.ativo else "Inativo"
        return f"{self.filial.nome} ({self.filial.cnpj}) - {status}"

    def delete(self, *args, **kwargs):
        # Remove o arquivo ao deletar o registro
        if self.arquivo_pfx:
            self.arquivo_pfx.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def cnpj_formatado(self):
        """Retorna o CNPJ da filial formatado"""
        cnpj = self.filial.cnpj
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj

    @property
    def esta_vencido(self):
        """Verifica se o certificado está vencido"""
        from django.utils import timezone
        return timezone.now().date() > self.data_validade


class NotaFiscal(models.Model):
    """
    Armazena metadados de NF-e baixadas da SEFAZ.
    O XML completo é armazenado em arquivo.
    """
    TIPO_CHOICES = [
        ('nfe', 'NF-e - Nota Fiscal Eletrônica'),
        ('cte', 'CT-e - Conhecimento de Transporte Eletrônico'),
        ('nfce', 'NFC-e - Nota Fiscal ao Consumidor Eletrônica'),
    ]

    STATUS_CHOICES = [
        ('pendente', 'Pendente de Análise'),
        ('vinculado', 'Vinculado a Conta'),
        ('importado', 'Importado como Conta'),
        ('descartado', 'Descartado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='notas_fiscais')
    filial = models.ForeignKey(
        Filial,
        on_delete=models.CASCADE,
        related_name='notas_fiscais',
        help_text='CNPJ destinatário da nota'
    )

    # Dados da NF-e
    chave_acesso = models.CharField(
        max_length=44,
        unique=True,
        verbose_name='Chave de Acesso',
        help_text='Chave de 44 dígitos da NF-e'
    )
    numero = models.CharField(
        max_length=20,
        verbose_name='Número',
        help_text='Número da nota fiscal'
    )
    serie = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Série'
    )
    tipo_documento = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default='nfe',
        verbose_name='Tipo'
    )

    # Datas
    data_emissao = models.DateTimeField(verbose_name='Data de Emissão')
    data_entrada_saida = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data Entrada/Saída'
    )

    # Emitente
    emitente_cnpj = models.CharField(max_length=14, verbose_name='CNPJ Emitente')
    emitente_nome = models.CharField(max_length=255, verbose_name='Razão Social Emitente')

    # Valores
    valor_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Valor Total'
    )
    valor_desconto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='Desconto'
    )
    valor_liquido = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name='Valor Líquido'
    )

    # Arquivo XML
    arquivo_xml = models.FileField(
        upload_to='notas_fiscais/%Y/%m/',
        help_text='Arquivo XML da NF-e'
    )

    # NSU
    nsu = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='NSU',
        help_text='Número Sequencial Único da SEFAZ'
    )

    # Status e controle
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente'
    )
    conta_pagar = models.ForeignKey(
        ContaPagar,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notas_fiscais',
        help_text='Conta a Pagar vinculada'
    )

    observacoes = models.TextField(
        blank=True,
        help_text='Observações sobre a nota'
    )

    # Auditoria
    importado_em = models.DateTimeField(auto_now_add=True)
    importado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Nota Fiscal Eletrônica'
        verbose_name_plural = 'Notas Fiscais Eletrônicas'
        ordering = ['-data_emissao']
        indexes = [
            models.Index(fields=['chave_acesso']),
            models.Index(fields=['emitente_cnpj']),
            models.Index(fields=['data_emissao']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"NF-e {self.numero} - {self.emitente_nome} - R$ {self.valor_total}"

    def save(self, *args, **kwargs):
        # Uppercase em campos de texto
        if self.emitente_nome:
            self.emitente_nome = self.emitente_nome.upper()
        if self.emitente_cnpj:
            self.emitente_cnpj = re.sub(r'\D', '', self.emitente_cnpj)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Remove o arquivo XML ao deletar
        if self.arquivo_xml:
            self.arquivo_xml.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def chave_formatada(self):
        """Retorna a chave de acesso formatada em grupos de 4"""
        chave = self.chave_acesso
        return ' '.join([chave[i:i+4] for i in range(0, len(chave), 4)])

    @property
    def cnpj_emitente_formatado(self):
        """Retorna o CNPJ do emitente formatado"""
        cnpj = self.emitente_cnpj
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj


class ConfiguracaoNFe(models.Model):
    """
    Configurações para importação automática de notas fiscais.
    Uma configuração por certificado digital.
    """

    STATUS_BUSCA_CHOICES = [
        ('inativa', 'Inativa'),
        ('ativa', 'Ativa'),
        ('executando', 'Executando'),
        ('erro', 'Erro'),
        ('concluida', 'Concluída'),
    ]

    certificado = models.OneToOneField(
        CertificadoDigital,
        on_delete=models.CASCADE,
        related_name='configuracao_nfe',
        verbose_name='Certificado Digital'
    )

    # Configurações de busca automática
    busca_automatica_ativa = models.BooleanField(
        default=False,
        verbose_name='Busca Automática Ativa',
        help_text='Se ativo, o sistema buscará novas notas automaticamente a cada 4 horas'
    )

    # Configurações de busca histórica
    busca_historica_ativa = models.BooleanField(
        default=False,
        verbose_name='Busca Histórica Ativa',
        help_text='Se ativo, o sistema buscará notas antigas de forma incremental'
    )

    busca_historica_status = models.CharField(
        max_length=20,
        choices=STATUS_BUSCA_CHOICES,
        default='inativa',
        verbose_name='Status da Busca Histórica'
    )

    busca_historica_progresso = models.IntegerField(
        default=0,
        verbose_name='Progresso da Busca Histórica (%)',
        help_text='Percentual de conclusão da busca histórica'
    )

    # Estatísticas
    ultima_execucao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Última Execução'
    )

    proximo_agendamento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Próximo Agendamento'
    )

    total_notas_importadas = models.IntegerField(
        default=0,
        verbose_name='Total de Notas Importadas',
        help_text='Total de notas importadas desde a ativação'
    )

    ultima_importacao_quantidade = models.IntegerField(
        default=0,
        verbose_name='Última Importação - Quantidade',
        help_text='Quantidade de notas importadas na última execução'
    )

    # Controle de erros
    ultimo_erro = models.TextField(
        blank=True,
        verbose_name='Último Erro'
    )

    data_ultimo_erro = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Data do Último Erro'
    )

    tentativas_erro = models.IntegerField(
        default=0,
        verbose_name='Tentativas com Erro',
        help_text='Contador de tentativas consecutivas com erro'
    )

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Configuração NFe'
        verbose_name_plural = 'Configurações NFe'
        db_table = 'configuracao_nfe'

    def __str__(self):
        status = "Ativa" if self.busca_automatica_ativa else "Inativa"
        return f"Config NFe - {self.certificado.filial.nome} ({status})"

    def registrar_execucao_sucesso(self, quantidade_importada):
        """Registra execução bem-sucedida"""
        from django.utils import timezone
        self.ultima_execucao = timezone.now()
        self.proximo_agendamento = timezone.now() + timezone.timedelta(hours=4)
        self.ultima_importacao_quantidade = quantidade_importada
        self.total_notas_importadas += quantidade_importada
        self.tentativas_erro = 0
        self.ultimo_erro = ''
        self.save()

    def registrar_erro(self, mensagem_erro):
        """Registra erro na execução"""
        from django.utils import timezone
        self.ultimo_erro = mensagem_erro[:500]  # Limita tamanho
        self.data_ultimo_erro = timezone.now()
        self.tentativas_erro += 1

        # Se tiver muitos erros consecutivos, desativa automaticamente
        if self.tentativas_erro >= 5:
            self.busca_automatica_ativa = False
            self.ultimo_erro += '\n\n[SISTEMA] Busca automática desativada após 5 tentativas com erro.'

        self.save()

