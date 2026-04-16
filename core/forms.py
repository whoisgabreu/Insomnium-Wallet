from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Receita, Despesa, GastoFixo

ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf']


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True, label='E-mail')
    first_name = forms.CharField(max_length=50, required=True, label='Nome')

    class Meta:
        model = User
        fields = ('first_name', 'username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['first_name'].widget.attrs['placeholder'] = 'Seu nome'
        self.fields['username'].widget.attrs['placeholder'] = 'Nome de usuário'
        self.fields['email'].widget.attrs['placeholder'] = 'seu@email.com'
        self.fields['password1'].widget.attrs['placeholder'] = '••••••••'
        self.fields['password2'].widget.attrs['placeholder'] = '••••••••'


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['username'].widget.attrs['placeholder'] = 'Nome de usuário'
        self.fields['password'].widget.attrs['placeholder'] = '••••••••'


class ReceitaForm(forms.ModelForm):
    class Meta:
        model = Receita
        fields = ['valor', 'descricao', 'data']
        widgets = {
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0,00'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Salário, Freelance...'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'valor': 'Valor (R$)',
            'descricao': 'Descrição',
            'data': 'Data',
        }


class DespesaForm(forms.ModelForm):
    class Meta:
        model = Despesa
        fields = ['valor', 'descricao', 'data', 'comprovante']
        widgets = {
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0,00'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Supermercado, Combustível...'}),
            'data': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'comprovante': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
        }
        labels = {
            'valor': 'Valor (R$)',
            'descricao': 'Descrição',
            'data': 'Data',
            'comprovante': 'Comprovante (opcional)',
        }

    def clean_comprovante(self):
        arquivo = self.cleaned_data.get('comprovante')
        if arquivo:
            ext = arquivo.name.split('.')[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f'Formato não permitido. Use: {", ".join(ALLOWED_EXTENSIONS)}'
                )
            if arquivo.size > 10 * 1024 * 1024:  # 10MB
                raise forms.ValidationError('Arquivo muito grande. Máximo: 10MB.')
        return arquivo


class GastoFixoForm(forms.ModelForm):
    class Meta:
        model = GastoFixo
        fields = ['nome', 'valor', 'dia_vencimento', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Aluguel, Internet, Academia...'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0,00'}),
            'dia_vencimento': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '31'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome': 'Nome',
            'valor': 'Valor (R$)',
            'dia_vencimento': 'Dia de Vencimento',
            'ativo': 'Ativo (recorrente)',
        }
