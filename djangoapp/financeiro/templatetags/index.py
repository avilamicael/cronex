# financeiro/templatetags/index.py

from django import template

register = template.Library()

@register.filter
def index(sequence, position):
    try:
        return sequence[position]
    except (IndexError, TypeError):
        return ''

@register.filter
def pertence_ao_grupo(user, nome_grupo):
    return user.groups.filter(name=nome_grupo).exists()
