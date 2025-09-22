from django.contrib import admin
from .models import ContaPagar, Filial, Transacao, Fornecedor, TipoPagamento
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

    change_list_template = "admin/contas_pagar_changelist.html"

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

    # --------------------
    # IMPORTAÇÃO
    # --------------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("importar/", self.admin_site.admin_view(self.importar_excel), name="contaspagar_importar"),
        ]
        return custom_urls + urls

    def importar_excel(self, request):
        if request.method == "POST":
            form = ImportarContasPagarForm(request.POST, request.FILES)
            if form.is_valid():
                arquivo = request.FILES['arquivo']
                wb = openpyxl.load_workbook(arquivo)
                ws = wb.active

                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not any(row):  # pula linha totalmente em branco
                        continue

                    (
                        filial_nome, transacao_nome, fornecedor_nome, tipo_pagamento_nome,
                        documento, descricao, numero_notas, codigo_barras,
                        data_mov, data_venc, data_pag, valor_bruto,
                        juros, multa, outros, desconto, valor_pago, saldo, status
                    ) = row[:19]  # garante que estamos pegando apenas as 19 colunas esperadas

                    empresa = Empresa.objects.first()

                    filial, _ = Filial.objects.get_or_create(empresa=empresa, nome=str(filial_nome).upper())
                    transacao, _ = Transacao.objects.get_or_create(empresa=empresa, nome=str(transacao_nome).upper())
                    tipo_pag, _ = TipoPagamento.objects.get_or_create(empresa=empresa, nome=str(tipo_pagamento_nome).upper())
                    fornecedor = None
                    if fornecedor_nome:
                        fornecedor, _ = Fornecedor.objects.get_or_create(empresa=empresa, nome=str(fornecedor_nome).upper())

                    # Função local para converter datas
                    def parse_data(valor):
                        if not valor:
                            return None
                        if isinstance(valor, datetime):
                            return valor.date()
                        try:
                            return datetime.strptime(str(valor), "%d/%m/%Y").date()
                        except:
                            return None

                    data_venc = parse_data(data_venc)
                    data_mov = parse_data(data_mov) or data_venc  # se data_mov estiver vazia, usa data_venc
                    data_pag = parse_data(data_pag)

                    ContaPagar.objects.create(
                        empresa=empresa,
                        filial=filial,
                        transacao=transacao,
                        fornecedor=fornecedor,
                        tipo_pagamento=tipo_pag,
                        documento=str(documento).upper() if documento else "",
                        descricao=str(descricao).upper() if descricao else "",
                        numero_notas=str(numero_notas) if numero_notas else "",
                        codigo_barras=str(codigo_barras) if codigo_barras else "",
                        data_movimentacao=data_mov,
                        data_vencimento=data_venc,
                        data_pagamento=data_pag,
                        valor_bruto=valor_bruto or 0,
                        valor_juros=juros or 0,
                        valor_multa=multa or 0,
                        outros_acrescimos=outros or 0,
                        valor_desconto=desconto or 0,
                        valor_pago=valor_pago or 0,
                        valor_saldo=saldo or 0,
                        status=self.map_status(status),
                        criado_por=request.user,
                    )

                self.message_user(request, "Importação concluída com sucesso!", level=messages.SUCCESS)
                return redirect("..")
        else:
            form = ImportarContasPagarForm()

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Importar Contas a Pagar",
        )
        return render(request, "admin/importar_contas_pagar.html", context)


    def parse_data(self, valor):
        if not valor:
            return None
        if isinstance(valor, datetime):
            return valor.date()
        try:
            return datetime.strptime(str(valor), "%d/%m/%Y").date()
        except:
            return None

    def map_status(self, valor):
        mapa = {
            "À Vencer": "a_vencer",
            "Pago": "pago",
            "Vencida": "vencida",
            "Cancelado": "cancelado",
        }
        return mapa.get(str(valor).strip(), "a_vencer")
