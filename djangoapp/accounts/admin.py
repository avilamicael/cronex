from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Empresa, User

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('username', 'email', 'empresa', 'nivel_acesso', 'is_staff')

    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('empresa', 'nivel_acesso')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'empresa', 'nivel_acesso', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )
