from django import forms
from .models import ContaPagar, Fornecedor, TipoPagamento
from django.utils.timezone import now
from django.forms import modelformset_factory
from .models import Filial

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

        hoje = now().date()
        if conta_pagar.data_vencimento < hoje:
            conta_pagar.status = 'vencida'
        else:
            conta_pagar.status = 'a_vencer'

        if commit:
            conta_pagar.save()
        return conta_pagar

class BaixaContaPagarForm(forms.ModelForm):
    class Meta:
        model = ContaPagar
        fields = [
            "data_pagamento",
            "valor_juros",
            "valor_multa",
            "valor_desconto",
            "outros_acrescimos",
        ]
        widgets = {
            "data_pagamento": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm", "style": "width: 120px;"}),
            "valor_juros": forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "width: 90px;"}),
            "valor_multa": forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "width: 90px;"}),
            "valor_desconto": forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "width: 90px;"}),
            "outros_acrescimos": forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "width: 90px;"}),
        }
        labels = {
            "data_pagamento": "Data de Pagamento",
            "valor_juros": "Juros",
            "valor_multa": "Multa",
            "valor_desconto": "Desconto",
            "outros_acrescimos": "Outros Acréscimos",
        }

    def clean(self):
        cd = super().clean()

        if not cd.get("data_pagamento"):
            self.add_error("data_pagamento", "A data de pagamento é obrigatória.")

        for campo in ("valor_juros", "valor_multa", "valor_desconto", "outros_acrescimos"):
            if cd.get(campo) and cd[campo] < 0:
                self.add_error(campo, "Valor não pode ser negativo.")
        return cd

# cria um formset sem extra forms
BaixaFormSet = modelformset_factory(
    ContaPagar,
    form=BaixaContaPagarForm,
    extra=0,
)

class ConciliacaoForm(forms.Form):
    filial = forms.ModelChoiceField(queryset=Filial.objects.all(), label='Filial')
    arquivo = forms.FileField(label='Arquivo OFX', help_text='Selecione o arquivo .OFX')

class ContaOFXForm(forms.Form):
    fornecedor = forms.CharField()
    valor = forms.DecimalField()
    data_pagamento = forms.DateField()
    descricao = forms.CharField(widget=forms.Textarea)
