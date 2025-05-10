# tarefas/forms.py
from django import forms
from .models import Tarefa
from django.utils import timezone
from datetime import datetime, timedelta

class TarefaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        agora = timezone.localtime()
        daqui_uma_hora_e_meia = agora + timedelta(minutes=90)

        self.initial['data'] = daqui_uma_hora_e_meia.date()
        self.initial['hora'] = daqui_uma_hora_e_meia.time().replace(second=0, microsecond=0)

        if user:
            self.fields['responsavel'].queryset = user.empresa.user_set.all()
            self.fields['responsavel'].initial = user

    data = forms.DateField(
        label='Data',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    hora = forms.TimeField(
        label='Hora',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )

    class Meta:
        model = Tarefa
        fields = ['titulo', 'descricao', 'responsavel']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título da tarefa'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descreva a tarefa'}),
            'responsavel': forms.Select(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        data = self.cleaned_data.get('data')
        hora = self.cleaned_data.get('hora')
        instance.data_execucao = timezone.make_aware(datetime.combine(data, hora))
        instance.data_para_notificar = instance.data_execucao - timedelta(
            minutes=instance.responsavel.tempo_antecedencia_minutos or 90
        )
        if commit:
            instance.save()
        return instance

class FinalizarTarefaForm(forms.Form):
    observacao = forms.CharField(
        label='Observação',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descreva o que foi feito...'})
    )

class RejeitarTarefaForm(forms.Form):
    observacao = forms.CharField(
        label='Motivo da Rejeição',
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

class RejeitarTarefaForm(forms.Form):
    observacao = forms.CharField(
        label='Motivo da Rejeição',
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explique por que está rejeitando a tarefa.'
        })
    )
