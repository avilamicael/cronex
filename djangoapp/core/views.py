from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q
from django.utils.timezone import now
from datetime import timedelta
from financeiro.models import Filial, RelatorioFaturamentoMensal, ContaPagar
from collections import defaultdict
import calendar
import json

@login_required
def dashboard_view(request):
    empresa = request.user.empresa
    hoje = now().date()
    inicio_mes = hoje.replace(day=1)
    # Último dia do mês atual
    ultimo_dia_mes = hoje.replace(day=calendar.monthrange(hoje.year, hoje.month)[1])
    proximos_7_dias = hoje + timedelta(days=7)

    # 1. CARDS DE RESUMO
    # Contas Pendentes (a_vencer + vencida)
    contas_pendentes = ContaPagar.objects.filter(
        empresa=empresa,
        status__in=['a_vencer', 'vencida']
    ).aggregate(
        total=Sum('valor_bruto'),
        quantidade=Count('id')
    )

    # Contas Vencidas
    contas_vencidas = ContaPagar.objects.filter(
        empresa=empresa,
        status='vencida'
    ).aggregate(
        total=Sum('valor_bruto'),
        quantidade=Count('id')
    )

    # Contas Pagas no Mês
    contas_pagas_mes = ContaPagar.objects.filter(
        empresa=empresa,
        status='pago',
        data_pagamento__gte=inicio_mes,
        data_pagamento__lte=ultimo_dia_mes
    ).aggregate(
        total=Sum('valor_pago'),
        quantidade=Count('id')
    )

    # Contas nos Próximos 7 Dias
    contas_proximos_7_dias = ContaPagar.objects.filter(
        empresa=empresa,
        status='a_vencer',
        data_vencimento__gte=hoje,
        data_vencimento__lte=proximos_7_dias
    ).aggregate(
        total=Sum('valor_bruto'),
        quantidade=Count('id')
    )

    # 2. GRÁFICO DE PAGAMENTOS POR DIA DO MÊS
    # Busca todas as contas a pagar do mês atual (pendentes)
    contas_por_dia = ContaPagar.objects.filter(
        empresa=empresa,
        status__in=['a_vencer', 'vencida'],
        data_vencimento__gte=inicio_mes,
        data_vencimento__lte=ultimo_dia_mes
    ).values(
        'data_vencimento', 'valor_bruto', 'fornecedor__nome'
    ).order_by('data_vencimento')

    # Agrupa por dia
    pagamentos_por_dia = defaultdict(lambda: {
        'valor_total': 0,
        'quantidade': 0,
        'fornecedores': []
    })

    for conta in contas_por_dia:
        dia = conta['data_vencimento'].day
        pagamentos_por_dia[dia]['valor_total'] += float(conta['valor_bruto'])
        pagamentos_por_dia[dia]['quantidade'] += 1
        fornecedor = conta['fornecedor__nome'] or 'Não informado'
        if fornecedor not in pagamentos_por_dia[dia]['fornecedores']:
            pagamentos_por_dia[dia]['fornecedores'].append(fornecedor)

    # Converte para lista ordenada
    chart_data = []
    dias_no_mes = calendar.monthrange(hoje.year, hoje.month)[1]
    for dia in range(1, dias_no_mes + 1):
        if dia in pagamentos_por_dia:
            chart_data.append({
                'dia': dia,
                'valor': pagamentos_por_dia[dia]['valor_total'],
                'quantidade': pagamentos_por_dia[dia]['quantidade'],
                'fornecedores': pagamentos_por_dia[dia]['fornecedores']
            })
        else:
            chart_data.append({
                'dia': dia,
                'valor': 0,
                'quantidade': 0,
                'fornecedores': []
            })

    # 3. TOP FORNECEDORES
    top_fornecedores = ContaPagar.objects.filter(
        empresa=empresa,
        status__in=['a_vencer', 'vencida']
    ).values(
        'fornecedor__id', 'fornecedor__nome'
    ).annotate(
        total=Sum('valor_bruto'),
        quantidade=Count('id')
    ).order_by('-total')[:10]  # Top 10 fornecedores

    # Busca o relatório mais recente da empresa do usuário
    ultimo_relatorio = RelatorioFaturamentoMensal.objects.filter(
        empresa=empresa
    ).first()

    return render(request, 'dashboard.html', {
        'ultimo_relatorio': ultimo_relatorio,
        'contas_pendentes': contas_pendentes,
        'contas_vencidas': contas_vencidas,
        'contas_pagas_mes': contas_pagas_mes,
        'contas_proximos_7_dias': contas_proximos_7_dias,
        'chart_data': json.dumps(chart_data),
        'top_fornecedores': top_fornecedores,
        'mes_atual': hoje.strftime('%B/%Y'),
    })

@login_required
@require_POST
def definir_filial_padrao(request):
    filial_id = request.POST.get('filial_padrao')
    if filial_id:
        try:
            filial = Filial.objects.get(id=filial_id, empresa=request.user.empresa)
            request.session['filial_padrao'] = filial.id
        except Filial.DoesNotExist:
            pass  # ignora se não existir
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
