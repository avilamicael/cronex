from django import forms
from .models import ContaPagar, Fornecedor, TipoPagamento
from django.utils.timezone import now

class ContaPagarForm(forms.ModelForm):
    class Meta:
        model = ContaPagar
        fields = [
            'filial', 'transacao', 'fornecedor', 'tipo_pagamento',
            'documento', 'descricao', 'numero_notas', 'codigo_barras',
            'data_movimentacao', 'data_vencimento',
            'valor_bruto',
        ]
        widgets = {
            'data_movimentacao': forms.DateInput(attrs={'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'filial': 'Filial',
            'transacao': 'Transação',
            'fornecedor': 'Fornecedor',
            'tipo_pagamento': 'Tipo de Pagamento',
            'documento': 'Documento',
            'descricao': 'Descrição',
            'numero_notas': 'Número(s) da(s) Nota(s)',
            'codigo_barras': 'Código de Barras',
            'data_movimentacao': 'Data de Movimentação',
            'data_vencimento': 'Data de Vencimento',
            'valor_bruto': 'Valor Bruto',
        }
        error_messages = {
            'documento': {
                'required': 'Informe o número do documento.',
            },
            'valor_bruto': {
                'required': 'Informe o valor bruto.',
                'invalid': 'Valor inválido.',
            },
            'data_vencimento': {
                'required': 'Informe a data de vencimento.',
            },
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        print(f"[FORM] Empresa recebida no form: {self.empresa}")

        if empresa:
            self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=empresa)
            self.fields['tipo_pagamento'].queryset = TipoPagamento.objects.filter(empresa=empresa)

        self.fields['data_movimentacao'].initial = now().date()


    def clean(self):
        cleaned_data = super().clean()
        valor_bruto = cleaned_data.get('valor_bruto')
        if valor_bruto is not None and valor_bruto <= 0:
            self.add_error('valor_bruto', 'O valor bruto deve ser maior que zero.')
        return cleaned_data

    def save(self, commit=True):
        conta_pagar = super().save(commit=False)
        conta_pagar.calcular_saldo()
        conta_pagar.status = 'pendente'  # padrão definido internamente
        if commit:
            conta_pagar.save()
        return conta_pagar
