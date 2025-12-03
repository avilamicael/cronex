"""
Forms para gestão de certificados digitais e consulta de NF-e.
"""
from django import forms
from django.core.exceptions import ValidationError
from financeiro.models import CertificadoDigital, Filial
from financeiro.crypto import encrypt_password
from datetime import datetime


class CertificadoDigitalForm(forms.ModelForm):
    """Form para upload e cadastro de certificado digital"""

    senha = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Senha do certificado'
        }),
        label='Senha do Certificado',
        help_text='A senha será criptografada antes de ser armazenada'
    )

    senha_confirmacao = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme a senha'
        }),
        label='Confirmar Senha',
        help_text='Digite a senha novamente'
    )

    class Meta:
        model = CertificadoDigital
        fields = ['filial', 'arquivo_pfx', 'uf_codigo', 'data_validade', 'ativo']
        widgets = {
            'filial': forms.Select(attrs={'class': 'form-select'}),
            'arquivo_pfx': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pfx,.p12'
            }),
            'uf_codigo': forms.Select(attrs={'class': 'form-select'}),
            'data_validade': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtra filiais pela empresa
        if empresa:
            self.fields['filial'].queryset = Filial.objects.filter(empresa=empresa)

        # Se está editando, não exige senha novamente
        if self.instance.pk:
            self.fields['senha'].required = False
            self.fields['senha_confirmacao'].required = False
            self.fields['senha'].help_text = 'Deixe em branco para manter a senha atual'

    def clean_arquivo_pfx(self):
        """Valida o arquivo do certificado"""
        arquivo = self.cleaned_data.get('arquivo_pfx')

        if arquivo:
            # Verifica extensão
            if not arquivo.name.endswith(('.pfx', '.p12')):
                raise ValidationError('O arquivo deve ser .pfx ou .p12')

            # Verifica tamanho (max 5MB)
            if arquivo.size > 5 * 1024 * 1024:
                raise ValidationError('O arquivo não pode ter mais de 5MB')

        return arquivo

    def clean(self):
        """Validações gerais do form"""
        cleaned_data = super().clean()
        senha = cleaned_data.get('senha')
        senha_confirmacao = cleaned_data.get('senha_confirmacao')

        # Se está editando e não forneceu senha, não valida
        if self.instance.pk and not senha:
            return cleaned_data

        # Validação de senhas
        if senha and senha_confirmacao:
            if senha != senha_confirmacao:
                raise ValidationError('As senhas não conferem')

        return cleaned_data

    def save(self, commit=True):
        """Salva o certificado com senha criptografada"""
        instance = super().save(commit=False)

        # Se forneceu uma nova senha, criptografa
        senha = self.cleaned_data.get('senha')
        if senha:
            instance.senha_encrypted = encrypt_password(senha)

        if commit:
            instance.save()

        return instance


class ConsultaNFeForm(forms.Form):
    """Form para consulta de NF-e na SEFAZ"""

    certificado = forms.ModelChoiceField(
        queryset=CertificadoDigital.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Certificado Digital',
        help_text='Selecione o CNPJ/Filial para consulta'
    )

    data_inicio = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data Início',
        help_text='Data inicial para busca das notas'
    )

    data_fim = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data Fim',
        help_text='Data final para busca das notas'
    )

    buscar_novos = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Buscar novos documentos',
        help_text='Busca documentos desde o último NSU consultado'
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtra certificados pela empresa (apenas ativos)
        if empresa:
            self.fields['certificado'].queryset = CertificadoDigital.objects.filter(
                empresa=empresa,
                ativo=True
            ).select_related('filial')

    def clean(self):
        """Validações gerais"""
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        # Valida período
        if data_inicio and data_fim:
            if data_inicio > data_fim:
                raise ValidationError('Data inicial não pode ser maior que data final')

            # Limita período a 3 meses
            delta = data_fim - data_inicio
            if delta.days > 90:
                raise ValidationError('O período não pode ser maior que 90 dias')

        # Valida certificado
        certificado = cleaned_data.get('certificado')
        if certificado and certificado.esta_vencido:
            raise ValidationError('O certificado selecionado está vencido')

        return cleaned_data


class FiltroNotasFiscaisForm(forms.Form):
    """Form para filtrar notas fiscais já importadas"""

    PERIODO_CHOICES = [
        ('hoje', 'Hoje'),
        ('7dias', 'Últimos 7 dias'),
        ('30dias', 'Últimos 30 dias'),
        ('mes_atual', 'Mês atual'),
        ('mes_anterior', 'Mês anterior'),
        ('personalizado', 'Período personalizado'),
    ]

    STATUS_CHOICES = [
        ('', 'Todos'),
        ('pendente', 'Pendente de Análise'),
        ('vinculado', 'Vinculado a Conta'),
        ('importado', 'Importado como Conta'),
        ('descartado', 'Descartado'),
    ]

    filial = forms.ModelChoiceField(
        queryset=Filial.objects.none(),
        required=False,
        empty_label='Todas as filiais',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Filial'
    )

    periodo = forms.ChoiceField(
        choices=PERIODO_CHOICES,
        initial='30dias',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Período'
    )

    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data Início'
    )

    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Data Fim'
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status'
    )

    emitente = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome ou CNPJ do emitente'
        }),
        label='Emitente'
    )

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtra filiais pela empresa
        if empresa:
            self.fields['filial'].queryset = Filial.objects.filter(empresa=empresa)


class VincularNotaContaForm(forms.Form):
    """Form para vincular uma nota fiscal a uma conta a pagar existente"""

    conta_pagar = forms.IntegerField(
        widget=forms.HiddenInput(),
        label='Conta a Pagar'
    )

    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observações sobre o vínculo (opcional)'
        }),
        label='Observações'
    )
