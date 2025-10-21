from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()

@register.filter(name='formatar_brl')
def formatar_brl(valor):
    """
    Formata um valor numérico para o padrão brasileiro (R$ 1.234,56)
    """
    if valor is None:
        return 'R$ 0,00'

    try:
        # Converte para Decimal se não for
        if not isinstance(valor, Decimal):
            valor = Decimal(str(valor))

        # Formata com separadores brasileiros
        valor_str = f"{valor:,.2f}"
        # Troca separadores: 1,234.56 -> 1.234,56
        valor_str = valor_str.replace(',', 'X').replace('.', ',').replace('X', '.')

        return f'R$ {valor_str}'
    except (ValueError, TypeError, InvalidOperation):
        return 'R$ 0,00'


@register.filter(name='mes_portugues')
def mes_portugues(data_str):
    """
    Converte nome do mês de inglês para português
    """
    meses = {
        'January': 'Janeiro',
        'February': 'Fevereiro',
        'March': 'Março',
        'April': 'Abril',
        'May': 'Maio',
        'June': 'Junho',
        'July': 'Julho',
        'August': 'Agosto',
        'September': 'Setembro',
        'October': 'Outubro',
        'November': 'Novembro',
        'December': 'Dezembro'
    }

    for ingles, portugues in meses.items():
        if ingles in str(data_str):
            data_str = str(data_str).replace(ingles, portugues)
            break

    return data_str
