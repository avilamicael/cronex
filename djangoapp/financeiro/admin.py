from django.contrib import admin
from .models import ContaPagar, Filial, Transacao, Fornecedor, TipoPagamento
import openpyxl
from django.http import HttpResponse

@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ['nome', 'empresa']
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
    list_display = ['transacao', 'valor_bruto', 'valor_pago', 'data_pagamento', 'data_vencimento', 'status', 'fornecedor']
    list_filter = ['empresa', 'status', 'data_vencimento', 'tipo_pagamento']
    search_fields = ['documento', 'transacao__nome', 'numero_notas', 'fornecedor__nome', 'tipo_pagamento__nome', 'data_pagamento', 'valor_bruto', 'valor_pago']
    date_hierarchy = 'data_vencimento'
    readonly_fields = ['valor_saldo', 'data_criacao', 'data_atualizacao', 'criado_por']
    actions = ['exportar_excel']

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'filial', 'transacao', 'fornecedor', 'tipo_pagamento')
        }),
        ('Detalhes do Documento', {
            'fields': ('documento', 'descricao', 'numero_notas', 'codigo_barras')
        }),
        ('Datas', {
            'fields': ('data_movimentacao', 'data_vencimento', 'data_pagamento')
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

    def exportar_excel(self, request, queryset):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Contas a Pagar"

        # Cabeçalhos
        headers = [
            'Filial', 'Transação', 'Fornecedor', 'Tipo de Pagamento', 'Documento',
            'Descrição', 'Nº Notas', 'Código de Barras', 'Data Movimentação',
            'Data Vencimento', 'Data Pagamento', 'Valor Bruto', 'Juros', 'Multa',
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
