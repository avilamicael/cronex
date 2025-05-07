from django import forms
from .models import User
import re

class UsuarioConfigForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telefone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sobrenome'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'E-mail'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Telefone'}),
        }
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'E-mail',
            'telefone': 'Telefone',
        }

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        if telefone:
            telefone = re.sub(r'\D', '', telefone)  # Remove qualquer caractere não numérico
            if len(telefone) < 10 or len(telefone) > 11:
                raise forms.ValidationError("Informe um telefone válido com DDD.")
        return telefone
