from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Empresa, User

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'endereco', 'telefone', 'responsavel', 'trial', 'ativo')
    # opcional: agrupar campos em seções
    fieldsets = (
        (None, {
            'fields': ('nome', 'cnpj')
        }),
        ('Contato e Endereço', {
            'fields': ('endereco', 'telefone', 'responsavel')
        }),
        ('Status e Observações', {
            'fields': ('observacao', 'trial', 'trial_expira_em', 'ativo')
        }),
        ('Informações de Sistema', {
            'fields': ('data_criacao',),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('data_criacao',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'empresa', 'telefone', 'telegram_chat_id',
        'ativo', 'is_staff', 'receber_notificacoes_de_subordinados',
        'tempo_antecedencia_minutos',
    )
    list_filter = ('is_staff', 'ativo', 'empresa')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Informações Pessoais', {
            'fields': (
                'first_name', 'last_name', 'email',
                'empresa', 'telefone', 'telegram_chat_id',
            )
        }),
        ('Permissões', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            )
        }),
        ('Datas Importantes', {
            'fields': ('last_login', 'date_joined'),
        }),
        ('Notificações', {
            'fields': ('receber_notificacoes_de_subordinados', 'tempo_antecedencia_minutos')
        }),

    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email',
                'first_name', 'last_name',
                'empresa', 'telefone', 'telegram_chat_id',
                'receber_notificacoes_de_subordinados',
                'tempo_antecedencia_minutos',
                'is_active', 'is_staff', 'is_superuser',
                'password1', 'password2',
            ),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions',)
