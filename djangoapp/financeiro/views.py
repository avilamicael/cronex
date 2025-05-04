from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ContaPagarForm
from .models import Filial, Transacao, Fornecedor, TipoPagamento

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
            return redirect('lancar_conta_pagar')
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
