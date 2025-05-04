from django.contrib import admin
from .models import ContaPagar, Filial, Transacao, Fornecedor, TipoPagamento

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
    list_display = ['transacao', 'valor_bruto', 'data_vencimento', 'status', 'fornecedor']
    list_filter = ['empresa', 'status', 'data_vencimento', 'tipo_pagamento']
    search_fields = ['documento', 'descricao', 'numero_notas', 'codigo_barras']
    date_hierarchy = 'data_vencimento'
    readonly_fields = ['valor_saldo', 'data_criacao', 'data_atualizacao', 'criado_por']
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
