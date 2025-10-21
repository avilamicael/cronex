from django import forms
from .models import ContaPagar, Fornecedor, TipoPagamento
from django.utils.timezone import now
from django.forms import modelformset_factory
from .models import Filial

class ContaPagarForm(forms.ModelForm):
    # Campos extras para controle de recorrência (não salvos diretamente no model)
    eh_recorrente = forms.BooleanField(
        required=False,
        initial=False,
        label='Esta conta é recorrente?',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_eh_recorrente'})
    )
    recorrencia_tipo = forms.ChoiceField(
        required=False,
        choices=[('', '--- Selecione ---')] + ContaPagar.RECORRENCIA_CHOICES,
        label='Tipo de recorrência',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_recorrencia_tipo'})
    )
    quantidade_recorrencias = forms.IntegerField(
        required=False,
        min_value=2,
        max_value=120,
        initial=2,
        label='Quantidade de contas a criar',
        help_text='Informe quantas contas serão criadas (mínimo 2, máximo 120)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_quantidade_recorrencias'})
    )

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

        # Valida campos de recorrência
        eh_recorrente = cleaned_data.get('eh_recorrente')
        if eh_recorrente:
            recorrencia_tipo = cleaned_data.get('recorrencia_tipo')
            quantidade_recorrencias = cleaned_data.get('quantidade_recorrencias')

            if not recorrencia_tipo:
                self.add_error('recorrencia_tipo', 'Selecione o tipo de recorrência.')

            if not quantidade_recorrencias:
                self.add_error('quantidade_recorrencias', 'Informe a quantidade de contas a criar.')
            elif quantidade_recorrencias < 2:
                self.add_error('quantidade_recorrencias', 'A quantidade mínima é 2 contas.')
            elif quantidade_recorrencias > 120:
                self.add_error('quantidade_recorrencias', 'A quantidade máxima é 120 contas.')

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
            "conta_bancaria_pagamento",
            "valor_juros",
            "valor_multa",
        ]
        widgets = {
            "data_pagamento": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm", "style": "width: 120px;"}),
            "conta_bancaria_pagamento": forms.Select(attrs={"class": "form-control form-control-sm select-banco", "style": "width: 150px;"}),
            "valor_juros": forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "width: 90px;"}),
            "valor_multa": forms.NumberInput(attrs={"class": "form-control form-control-sm", "style": "width: 90px;"}),
        }
        labels = {
            "data_pagamento": "Data de Pagamento",
            "conta_bancaria_pagamento": "Banco",
            "valor_juros": "Juros",
            "valor_multa": "Multa",
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)

        if empresa:
            self.fields['conta_bancaria_pagamento'].queryset = Filial.objects.filter(empresa=empresa)

        # Torna o campo de banco obrigatório
        self.fields['conta_bancaria_pagamento'].required = True

    def clean(self):
        cd = super().clean()

        if not cd.get("data_pagamento"):
            self.add_error("data_pagamento", "A data de pagamento é obrigatória.")

        if not cd.get("conta_bancaria_pagamento"):
            self.add_error("conta_bancaria_pagamento", "Selecione a conta bancária para pagamento.")

        for campo in ("valor_juros", "valor_multa"):
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
    filial = forms.ModelChoiceField(
        queryset=Filial.objects.all(),
        label='Filial',
        widget=forms.Select(attrs={
            'class': 'form-select rounded-pill',  # Bootstrap 5 + estilo "menos quadrado"
            'style': 'max-width: 300px;',         # opcional: controla largura
        })
    )
    arquivo = forms.FileField(
        label='Arquivo OFX',
        help_text='Apenas arquivos .OFX',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'style': 'max-width: 300px;',
            'accept': '.ofx'  # <- esta linha limita no navegador
        })
    )
class ContaOFXForm(forms.Form):
    fornecedor = forms.CharField()
    valor = forms.DecimalField()
    data_pagamento = forms.DateField()
    descricao = forms.CharField(widget=forms.Textarea)
