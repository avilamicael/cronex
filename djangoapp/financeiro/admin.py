from django.contrib import admin
from .models import ContaPagar, Filial, Transacao, Fornecedor, TipoPagamento, RelatorioFaturamentoMensal, CertificadoDigital, NotaFiscal, ConfiguracaoNFe
from accounts.models import Empresa
import openpyxl
from django.http import HttpResponse
from datetime import datetime
from django.shortcuts import render, redirect
from .forms import ImportarContasPagarForm
from django.contrib import messages
from django.urls import path

@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa', 'conta_bancaria']
    list_filter = ['empresa']
    search_fields = ['nome']

@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa']
    list_filter = ['empresa']
    search_fields = ['nome']

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cnpj', 'empresa']
    list_filter = ['empresa']
    search_fields = ['nome', 'cnpj']

@admin.register(TipoPagamento)
class TipoPagamentoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa']
    list_filter = ['empresa']
    search_fields = ['nome']

@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = ['transacao', 'valor_bruto', 'valor_pago', 'data_pagamento', 'conta_bancaria_pagamento', 'data_vencimento', 'status', 'fornecedor']
    list_filter = ['empresa', 'status', 'data_vencimento', 'tipo_pagamento', 'conta_bancaria_pagamento']
    search_fields = ['documento', 'transacao__nome', 'numero_notas', 'fornecedor__nome', 'tipo_pagamento__nome', 'data_pagamento', 'valor_bruto', 'valor_pago']
    date_hierarchy = 'data_vencimento'
    readonly_fields = ['valor_saldo', 'data_criacao', 'data_atualizacao', 'criado_por']
    actions = ['exportar_excel']

    change_list_template = "admin/contas_pagar_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('importar/', self.admin_site.admin_view(self.importar_view), name='contaspagar_importar'),
        ]
        return custom_urls + urls

    def importar_view(self, request):
        """View para importar contas a pagar via Excel"""
        if request.method == 'POST':
            form = ImportarContasPagarForm(request.POST, request.FILES)
            if form.is_valid():
                arquivo = request.FILES['arquivo']
                # TODO: Implementar lógica de importação
                messages.success(request, "Arquivo enviado com sucesso! (Importação a ser implementada)")
                return redirect('..')
        else:
            form = ImportarContasPagarForm()

        context = {
            'form': form,
            'title': 'Importar Contas a Pagar',
            'site_header': 'Importação de Contas',
        }
        return render(request, 'admin/importar_contas.html', context)

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'filial', 'transacao', 'fornecedor', 'tipo_pagamento')
        }),
        ('Detalhes do Documento', {
            'fields': ('documento', 'descricao', 'numero_notas', 'codigo_barras')
        }),
        ('Datas e Pagamento', {
            'fields': ('data_movimentacao', 'data_vencimento', 'data_pagamento', 'conta_bancaria_pagamento')
        }),
        ('Valores', {
            'fields': (
                'valor_bruto', 'valor_juros', 'valor_multa',
                'outros_acrescimos', 'valor_desconto', 'valor_pago', 'valor_saldo'
            )
        }),
        ('Outros', {
            'fields': ('status', 'criado_por', 'data_criacao', 'data_atualizacao')
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.criado_por:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)

    # --------------------
    # EXPORTAÇÃO
    # --------------------
    def exportar_excel(self, request, queryset):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Contas a Pagar"

        headers = [
            'Filial', 'Transação', 'Fornecedor', 'Tipo de Pagamento', 'Documento',
            'Descrição', 'Nº Notas', 'Código de Barras', 'Data Movimentação',
            'Data Vencimento', 'Data Pagamento', 'Banco Pagamento', 'Valor Bruto', 'Juros', 'Multa',
            'Outros Acréscimos', 'Desconto', 'Valor Pago', 'Saldo', 'Status'
        ]
        ws.append(headers)

        for conta in queryset:
            ws.append([
                conta.filial.nome,
                conta.transacao.nome,
                conta.fornecedor.nome if conta.fornecedor else '',
                conta.tipo_pagamento.nome,
                conta.documento,
                conta.descricao,
                conta.numero_notas,
                conta.codigo_barras,
                conta.data_movimentacao.strftime('%d/%m/%Y'),
                conta.data_vencimento.strftime('%d/%m/%Y'),
                conta.data_pagamento.strftime('%d/%m/%Y') if conta.data_pagamento else '',
                conta.conta_bancaria_pagamento.nome if conta.conta_bancaria_pagamento else '',
                float(conta.valor_bruto),
                float(conta.valor_juros),
                float(conta.valor_multa),
                float(conta.outros_acrescimos),
                float(conta.valor_desconto),
                float(conta.valor_pago),
                float(conta.valor_saldo),
                conta.get_status_display()
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=contas_a_pagar.xlsx'
        wb.save(response)
        return response

    exportar_excel.short_description = "Exportar selecionadas para Excel"

@admin.register(RelatorioFaturamentoMensal)
class RelatorioFaturamentoMensalAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'mes_ano_formatado', 'data_geracao', 'tem_arquivo']
    list_filter = ['empresa', 'ano', 'mes']
    search_fields = ['empresa__nome']
    readonly_fields = ['data_geracao', 'gerado_por', 'arquivo_zip']
    ordering = ['-ano', '-mes']
    actions = ['gerar_relatorio_action']

    def mes_ano_formatado(self, obj):
        return obj.mes_ano_formatado
    mes_ano_formatado.short_description = 'Período'

    def tem_arquivo(self, obj):
        return bool(obj.arquivo_zip)
    tem_arquivo.short_description = 'Arquivo'
    tem_arquivo.boolean = True

    def gerar_relatorio_action(self, request, queryset):
        """Action para gerar/regenerar relatórios selecionados"""
        from financeiro.tasks import gerar_relatorio_faturamento_mensal
        from django.contrib import messages

        count = 0
        for relatorio in queryset:
            try:
                # Chama a task de forma síncrona (roda imediatamente)
                resultado = gerar_relatorio_faturamento_mensal(
                    mes_ref=relatorio.mes,
                    ano_ref=relatorio.ano
                )
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Erro ao gerar relatório {relatorio.mes:02d}/{relatorio.ano}: {str(e)}",
                    level=messages.ERROR
                )

        if count > 0:
            self.message_user(
                request,
                f"{count} relatório(s) gerado(s) com sucesso!",
                level=messages.SUCCESS
            )

    gerar_relatorio_action.short_description = "Gerar/Regenerar relatórios selecionados"


# ========================================
# ADMIN - NOTAS FISCAIS ELETRÔNICAS
# ========================================

@admin.register(CertificadoDigital)
class CertificadoDigitalAdmin(admin.ModelAdmin):
    list_display = ['filial', 'empresa', 'uf_codigo', 'data_validade', 'ativo', 'esta_vencido', 'criado_em']
    list_filter = ['empresa', 'ativo', 'uf_codigo', 'data_validade']
    search_fields = ['filial__nome', 'filial__cnpj']
    readonly_fields = ['criado_em', 'atualizado_em', 'criado_por', 'senha_encrypted']
    ordering = ['-ativo', 'filial__nome']

    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'filial', 'uf_codigo')
        }),
        ('Certificado', {
            'fields': ('arquivo_pfx', 'senha_encrypted', 'data_validade', 'ativo')
        }),
        ('Controle SEFAZ', {
            'fields': ('ultimo_nsu',)
        }),
        ('Auditoria', {
            'fields': ('criado_em', 'atualizado_em', 'criado_por'),
            'classes': ('collapse',)
        }),
    )

    def esta_vencido(self, obj):
        return obj.esta_vencido
    esta_vencido.short_description = 'Vencido'
    esta_vencido.boolean = True


@admin.register(NotaFiscal)
class NotaFiscalAdmin(admin.ModelAdmin):
    list_display = ['numero', 'data_emissao', 'emitente_nome', 'valor_total', 'status', 'filial', 'importado_em']
    list_filter = ['empresa', 'status', 'tipo_documento', 'filial', 'data_emissao']
    search_fields = ['numero', 'chave_acesso', 'emitente_nome', 'emitente_cnpj']
    readonly_fields = ['importado_em', 'importado_por', 'atualizado_em', 'chave_formatada']
    date_hierarchy = 'data_emissao'
    ordering = ['-data_emissao']
    actions = ['marcar_como_vinculado', 'marcar_como_descartado']

    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'filial', 'tipo_documento', 'numero', 'serie', 'chave_acesso', 'chave_formatada')
        }),
        ('Datas', {
            'fields': ('data_emissao', 'data_entrada_saida')
        }),
        ('Emitente', {
            'fields': ('emitente_nome', 'emitente_cnpj')
        }),
        ('Valores', {
            'fields': ('valor_total', 'valor_desconto', 'valor_liquido')
        }),
        ('Controle', {
            'fields': ('status', 'conta_pagar', 'nsu', 'arquivo_xml', 'observacoes')
        }),
        ('Auditoria', {
            'fields': ('importado_em', 'importado_por', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def marcar_como_vinculado(self, request, queryset):
        count = queryset.update(status='vinculado')
        self.message_user(request, f"{count} nota(s) marcada(s) como vinculada(s).", level=messages.SUCCESS)
    marcar_como_vinculado.short_description = "Marcar como vinculado"

    def marcar_como_descartado(self, request, queryset):
        count = queryset.update(status='descartado')
        self.message_user(request, f"{count} nota(s) marcada(s) como descartada(s).", level=messages.SUCCESS)
    marcar_como_descartado.short_description = "Marcar como descartado"



@admin.register(ConfiguracaoNFe)
class ConfiguracaoNFeAdmin(admin.ModelAdmin):
    list_display = [
        "certificado",
        "busca_automatica_ativa",
        "busca_historica_status",
        "ultima_execucao",
        "proximo_agendamento",
        "total_notas_importadas",
        "tentativas_erro"
    ]
    list_filter = ["busca_automatica_ativa", "busca_historica_ativa", "busca_historica_status"]
    search_fields = ["certificado__filial__nome", "certificado__filial__cnpj"]
    readonly_fields = [
        "ultima_execucao",
        "proximo_agendamento",
        "total_notas_importadas",
        "ultima_importacao_quantidade",
        "ultimo_erro",
        "data_ultimo_erro",
        "tentativas_erro",
        "criado_em",
        "atualizado_em"
    ]

    fieldsets = (
        ("Certificado", {
            "fields": ("certificado",)
        }),
        ("Busca Automática", {
            "fields": (
                "busca_automatica_ativa",
                "ultima_execucao",
                "proximo_agendamento",
            )
        }),
        ("Busca Histórica", {
            "fields": (
                "busca_historica_ativa",
                "busca_historica_status",
                "busca_historica_progresso",
            )
        }),
        ("Estatísticas", {
            "fields": (
                "total_notas_importadas",
                "ultima_importacao_quantidade",
            )
        }),
        ("Controle de Erros", {
            "fields": (
                "ultimo_erro",
                "data_ultimo_erro",
                "tentativas_erro",
            ),
            "classes": ("collapse",)
        }),
        ("Auditoria", {
            "fields": ("criado_em", "atualizado_em"),
            "classes": ("collapse",)
        }),
    )

    def has_delete_permission(self, request, obj=None):
        return True

