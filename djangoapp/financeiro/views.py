from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.views.decorators.http import require_POST
import os
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from .forms import ContaPagarForm
from .models import Filial, Transacao, Fornecedor, TipoPagamento, ContaPagar, RelatorioFaturamentoMensal
from financeiro.contas.incluir_contas import _importar_csv, _importar_xml
from core.decorators import grupos_necessarios
from .forms import ConciliacaoForm, ContaOFXForm
from .utils import processar_ofx
from .recorrencia import criar_contas_recorrentes
from django.db.models import Q

@grupos_necessarios("Administrador", "Financeiro")
@login_required
def lancar_conta_pagar(request):
    empresa = request.user.empresa

    if request.method == 'POST':
        form = ContaPagarForm(request.POST, empresa=empresa)
        if form.is_valid():
            # Verifica se é conta recorrente
            eh_recorrente = form.cleaned_data.get('eh_recorrente')

            if eh_recorrente:
                # Cria múltiplas contas recorrentes
                tipo_recorrencia = form.cleaned_data.get('recorrencia_tipo')
                quantidade = form.cleaned_data.get('quantidade_recorrencias')

                # Prepara a conta base (não salva ainda)
                conta_base = form.save(commit=False)
                conta_base.empresa = empresa
                conta_base.criado_por = request.user

                # Cria todas as contas recorrentes
                contas_criadas = criar_contas_recorrentes(
                    conta_base=conta_base,
                    tipo_recorrencia=tipo_recorrencia,
                    quantidade=quantidade,
                    empresa=empresa,
                    usuario=request.user
                )

                messages.success(
                    request,
                    f"{len(contas_criadas)} contas recorrentes criadas com sucesso! "
                    f"({tipo_recorrencia.capitalize()} - {quantidade} parcelas)"
                )
            else:
                # Conta única (comportamento normal)
                conta = form.save(commit=False)
                conta.empresa = empresa
                conta.criado_por = request.user
                conta.save()
                messages.success(request, "Conta incluída com sucesso.")

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

@grupos_necessarios("Administrador", "Financeiro")
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

    # Força o filtro "à pagar" no primeiro acesso (sem nenhum filtro enviado)
    if 'status' not in request.GET:
        status = 'a_pagar'

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

    filtros['status'] = status

    contas = contas.order_by('data_vencimento')

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

@grupos_necessarios("Administrador", "Financeiro")
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

@grupos_necessarios("Administrador", "Financeiro")
@login_required
def concilia_contas_view(request):
    empresa = request.user.empresa
    
    # Buscar dados para o formulário do modal (sempre disponível)
    filiais = Filial.objects.filter(empresa=empresa)
    transacoes = Transacao.objects.filter(empresa=empresa)
    fornecedores = Fornecedor.objects.filter(empresa=empresa)
    tipos_pagamento = TipoPagamento.objects.filter(empresa=empresa)
    
    if request.method == 'POST':
        form = ConciliacaoForm(request.POST, request.FILES)
        if form.is_valid():
            filial = form.cleaned_data['filial']
            arquivo = form.cleaned_data['arquivo']

            contas_banco = processar_ofx(arquivo)

            mes = contas_banco[0]['data'].month
            ano = contas_banco[0]['data'].year

            # Busca contas que foram pagas pela conta bancária selecionada
            # Fallback: se conta_bancaria_pagamento for null, usa a filial (dados antigos)
            contas_sistema = ContaPagar.objects.filter(
                Q(conta_bancaria_pagamento=filial) | 
                Q(conta_bancaria_pagamento__isnull=True, filial=filial),
                status='pago',
                data_pagamento__month=mes,
                data_pagamento__year=ano
            )

            contas_usadas = set()

            for item in contas_banco:
                item['conciliado'] = False
                item_valor = Decimal(item['valor'])
                item_data = item['data'].date() if hasattr(item['data'], 'date') else item['data']

                for conta in contas_sistema:
                    valor_pgto = conta.valor_pago if conta.valor_pago is not None else conta.valor_bruto
                    conta_valor = Decimal(valor_pgto)
                    conta_data = conta.data_pagamento

                    if (
                        abs(conta_valor - item_valor) < Decimal('0.01') and
                        conta_data == item_data and
                        conta.id not in contas_usadas
                    ):
                        item['conciliado'] = True
                        contas_usadas.add(conta.id)
                        break

            contas_nao_conciliadas = contas_sistema.exclude(id__in=contas_usadas)

            return render(request, 'financeiro/concilia_resultado.html', {
                'contas_banco': contas_banco,
                'contas_nao_conciliadas': contas_nao_conciliadas,
                'filial': filial,
                'filiais': filiais,
                'transacoes': transacoes,
                'fornecedores': fornecedores,
                'tipos_pagamento': tipos_pagamento,
            })

    else:
        form = ConciliacaoForm()

    return render(request, 'financeiro/concilia_form.html', {
        'form': form,
    })

@require_POST
@login_required
@grupos_necessarios("Administrador", "Financeiro")
def incluir_conta_conciliacao(request):
    """
    Cria uma nova conta a pagar a partir dos dados do extrato bancário
    """
    try:
        empresa = request.user.empresa
        
        # Dados obrigatórios
        filial_id = request.POST.get("filial_id")
        transacao_id = request.POST.get("transacao_id")
        tipo_pagamento_id = request.POST.get("tipo_pagamento_id")
        documento = request.POST.get("documento")
        data_movimentacao = request.POST.get("data_movimentacao")
        data_vencimento = request.POST.get("data_vencimento")
        data_pagamento = request.POST.get("data_pagamento")
        valor = request.POST.get("valor").replace(',', '.')
        
        # Dados opcionais
        fornecedor_id = request.POST.get("fornecedor_id")
        conta_bancaria_pagamento_id = request.POST.get("conta_bancaria_pagamento_id")
        descricao = request.POST.get("descricao", "")
        numero_notas = request.POST.get("numero_notas", "")
        
        # Validações básicas
        if not all([filial_id, transacao_id, tipo_pagamento_id, documento, 
                    data_movimentacao, data_vencimento, data_pagamento, valor]):
            messages.error(request, "Todos os campos obrigatórios devem ser preenchidos!")
            return redirect("concilia_contas")
        
        # Criar a conta
        conta = ContaPagar.objects.create(
            empresa=empresa,
            filial=Filial.objects.get(id=filial_id, empresa=empresa),
            transacao=Transacao.objects.get(id=transacao_id, empresa=empresa),
            tipo_pagamento=TipoPagamento.objects.get(id=tipo_pagamento_id, empresa=empresa),
            fornecedor=Fornecedor.objects.get(id=fornecedor_id, empresa=empresa) if fornecedor_id else None,
            conta_bancaria_pagamento=Filial.objects.get(id=conta_bancaria_pagamento_id, empresa=empresa) if conta_bancaria_pagamento_id else None,
            documento=documento,
            descricao=descricao,
            numero_notas=numero_notas,
            data_movimentacao=data_movimentacao,
            data_vencimento=data_vencimento,
            data_pagamento=data_pagamento,
            valor_bruto=Decimal(valor),
            valor_pago=Decimal(valor),
            status="pago",
            criado_por=request.user
        )
        
        messages.success(request, f"Conta '{documento}' adicionada e conciliada com sucesso!")
        
    except Exception as e:
        messages.error(request, f"Erro ao criar conta: {str(e)}")
    
    return redirect("concilia_contas")

@login_required
@grupos_necessarios("Administrador", "Financeiro", "Gestor")
def download_relatorio_faturamento(request, relatorio_id):
    """
    View segura para download do relatório de faturamento mensal.

    Proteções:
    - Requer autenticação (@login_required)
    - Requer grupo Administrador, Financeiro ou Gestor
    - Valida que o relatório pertence à empresa do usuário
    - Serve arquivo via Django (não expõe caminho direto)
    """
    relatorio = get_object_or_404(
        RelatorioFaturamentoMensal,
        id=relatorio_id,
        empresa=request.user.empresa
    )

    if not relatorio.arquivo_zip:
        raise Http404("Arquivo não encontrado.")

    # Retorna o arquivo para download de forma segura
    response = FileResponse(relatorio.arquivo_zip.open('rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(relatorio.arquivo_zip.name)}"'

    # Headers de segurança adicionais
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Type'] = 'application/zip'

    return response
