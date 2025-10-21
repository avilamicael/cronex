# financeiro/recorrencia.py
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import uuid


def calcular_proxima_data(data_base, tipo_recorrencia, numero_parcela):
    """
    Calcula a próxima data de vencimento baseada no tipo de recorrência.

    Args:
        data_base: Data inicial (data do primeiro vencimento)
        tipo_recorrencia: Tipo de recorrência (semanal, mensal, etc)
        numero_parcela: Número da parcela (1, 2, 3, ...)

    Returns:
        Data calculada para a parcela
    """
    if numero_parcela == 1:
        return data_base

    incremento = numero_parcela - 1

    if tipo_recorrencia == 'semanal':
        return data_base + timedelta(days=7 * incremento)
    elif tipo_recorrencia == 'quinzenal':
        return data_base + timedelta(days=15 * incremento)
    elif tipo_recorrencia == 'mensal':
        return data_base + relativedelta(months=incremento)
    elif tipo_recorrencia == 'bimestral':
        return data_base + relativedelta(months=2 * incremento)
    elif tipo_recorrencia == 'trimestral':
        return data_base + relativedelta(months=3 * incremento)
    elif tipo_recorrencia == 'semestral':
        return data_base + relativedelta(months=6 * incremento)
    elif tipo_recorrencia == 'anual':
        return data_base + relativedelta(months=12 * incremento)
    else:
        return data_base


def criar_contas_recorrentes(conta_base, tipo_recorrencia, quantidade, empresa, usuario):
    """
    Cria múltiplas contas recorrentes baseadas em uma conta base.

    Args:
        conta_base: Instância da ContaPagar original (não salva ainda)
        tipo_recorrencia: Tipo de recorrência
        quantidade: Quantidade total de contas a criar
        empresa: Empresa do usuário
        usuario: Usuário que está criando

    Returns:
        Lista de contas criadas
    """
    from financeiro.models import ContaPagar
    from django.utils.timezone import now

    # Gera um ID único para agrupar essas contas recorrentes
    grupo_id = f"REC-{uuid.uuid4().hex[:12].upper()}"

    contas_criadas = []
    hoje = now().date()

    for i in range(1, quantidade + 1):
        # Calcula as datas para esta parcela
        nova_data_vencimento = calcular_proxima_data(
            conta_base.data_vencimento,
            tipo_recorrencia,
            i
        )
        nova_data_movimentacao = calcular_proxima_data(
            conta_base.data_movimentacao,
            tipo_recorrencia,
            i
        )

        # Determina o status baseado na data de vencimento
        if nova_data_vencimento < hoje:
            status = 'vencida'
        else:
            status = 'a_vencer'

        # Cria a conta
        conta = ContaPagar.objects.create(
            # Dados base
            empresa=empresa,
            filial=conta_base.filial,
            transacao=conta_base.transacao,
            fornecedor=conta_base.fornecedor,
            tipo_pagamento=conta_base.tipo_pagamento,

            # Documento e descrição com indicação de parcela
            documento=f"{conta_base.documento} ({i}/{quantidade})",
            descricao=conta_base.descricao,
            numero_notas=conta_base.numero_notas,
            codigo_barras=conta_base.codigo_barras,

            # Datas calculadas
            data_movimentacao=nova_data_movimentacao,
            data_vencimento=nova_data_vencimento,

            # Valores
            valor_bruto=conta_base.valor_bruto,
            valor_juros=conta_base.valor_juros,
            valor_multa=conta_base.valor_multa,
            outros_acrescimos=conta_base.outros_acrescimos,
            valor_desconto=conta_base.valor_desconto,

            # Status e metadados
            status=status,
            criado_por=usuario,

            # Campos de recorrência
            eh_recorrente=True,
            recorrencia_tipo=tipo_recorrencia,
            recorrencia_grupo=grupo_id,
            numero_parcela=i,
            total_parcelas=quantidade,
        )

        contas_criadas.append(conta)

    return contas_criadas
