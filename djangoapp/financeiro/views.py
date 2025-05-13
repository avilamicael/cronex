from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
import os
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ContaPagarForm
from .models import Filial, Transacao, Fornecedor, TipoPagamento, ContaPagar
from financeiro.contas.incluir_contas import _importar_csv, _importar_xml

@login_required
def lancar_conta_pagar(request):
    empresa = request.user.empresa

    if request.method == 'POST':
        form = ContaPagarForm(request.POST, empresa=empresa)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.empresa = empresa
            conta.criado_por = request.user
            conta.save()
            messages.success(request, "Conta incluida com sucesso.")
            return redirect('lancar_conta_pagar')
        else:
            messages.error(request, "Erro ao lançar a conta. Verifique os campos obrigatórios.")
    else:
        # Obtem a filial padrão da sessão (se houver)
        filial_padrao_id = request.session.get('filial_padrao')
        initial_data = {}
        if filial_padrao_id:
            initial_data['filial'] = filial_padrao_id

        form = ContaPagarForm(empresa=empresa, initial=initial_data)

    # Dados adicionais para renderização
    filiais = Filial.objects.filter(empresa=empresa)
    transacoes = Transacao.objects.filter(empresa=empresa)
    fornecedores = Fornecedor.objects.filter(empresa=empresa)
    tipos_pagamento = TipoPagamento.objects.filter(empresa=empresa)

    return render(request, 'financeiro/contas/lancar_conta_pagar.html', {
        'form': form,
        'filiais': filiais,
        'transacoes': transacoes,
        'fornecedores': fornecedores,
        'tipos_pagamento': tipos_pagamento,
    })

@login_required
def listar_contas_pagar(request):
    empresa = request.user.empresa
    contas = ContaPagar.objects.filter(empresa=empresa)

    # Filtros múltiplos
    filial_ids = request.GET.getlist('filial')
    transacao_ids = request.GET.getlist('transacao')
    fornecedor_ids = request.GET.getlist('fornecedor')
    tipo_pagamento_ids = request.GET.getlist('tipo_pagamento')

    if filial_ids:
        contas = contas.filter(filial_id__in=filial_ids)
    if transacao_ids:
        contas = contas.filter(transacao_id__in=transacao_ids)
    if fornecedor_ids:
        contas = contas.filter(fornecedor_id__in=fornecedor_ids)
    if tipo_pagamento_ids:
        contas = contas.filter(tipo_pagamento_id__in=tipo_pagamento_ids)

    # Campos texto
    documento = request.GET.get('documento')
    numero_notas = request.GET.get('numero_notas')
    if documento:
        contas = contas.filter(documento__icontains=documento)
    if numero_notas:
        contas = contas.filter(numero_notas__icontains=numero_notas)

    # Datas
    vencimento_de = request.GET.get('vencimento_de')
    vencimento_ate = request.GET.get('vencimento_ate')
    movimentacao_de = request.GET.get('movimentacao_de')
    movimentacao_ate = request.GET.get('movimentacao_ate')

    if vencimento_de:
        contas = contas.filter(data_vencimento__gte=vencimento_de)
    if vencimento_ate:
        contas = contas.filter(data_vencimento__lte=vencimento_ate)
    if movimentacao_de:
        contas = contas.filter(data_movimentacao__gte=movimentacao_de)
    if movimentacao_ate:
        contas = contas.filter(data_movimentacao__lte=movimentacao_ate)

    # Status
    status = request.GET.get('status')

    if status == 'a_pagar':
        contas = contas.filter(status__in=['a_vencer', 'vencida'])
    elif status:
        contas = contas.filter(status=status)
    # se status estiver vazio ou não for passado, exibe todas



    # Preparar nomes para manter os selects carregados
    filtros = request.GET.copy()

    filtros['filial_ids'] = filial_ids
    filtros['filial_nomes'] = list(Filial.objects.filter(id__in=filial_ids).values_list('id', 'nome'))

    filtros['transacao_ids'] = transacao_ids
    filtros['transacao_nomes'] = list(Transacao.objects.filter(id__in=transacao_ids).values_list('id', 'nome'))

    filtros['fornecedor_ids'] = fornecedor_ids
    filtros['fornecedor_nomes'] = list(Fornecedor.objects.filter(id__in=fornecedor_ids).values_list('id', 'nome'))

    filtros['tipo_pagamento_ids'] = tipo_pagamento_ids
    filtros['tipo_pagamento_nomes'] = list(TipoPagamento.objects.filter(id__in=tipo_pagamento_ids).values_list('id', 'nome'))

    # ---------- PAGINAÇÃO ----------
    page_size = int(request.GET.get("page_size", 25))         # default 25 linhas
    paginator = Paginator(contas, page_size)

    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, "financeiro/contas/listar_contas_pagar.html", {
        "contas": page_obj.object_list,   # só as da página atual
        "page_obj": page_obj,             # usado no template
        "filtros": filtros,
        "page_size": page_size,
        "sizes": [10, 25, 50, 100],
    })

@login_required
def importar_contas_arquivo(request):
    empresa = request.user.empresa

    if request.method == 'POST' and request.FILES.getlist('arquivo'):
        arquivos = request.FILES.getlist('arquivo')
        for arquivo in arquivos:
            ext = os.path.splitext(arquivo.name)[1].lower()
            if ext == '.csv':
                _importar_csv(arquivo, request, empresa)
            elif ext == '.xml':
                _importar_xml(arquivo, request, empresa)
            else:
                messages.error(request, f"Formato não suportado: {arquivo.name}")
    return redirect('lancar_conta_pagar')
