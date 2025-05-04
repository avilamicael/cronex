from financeiro.models import Filial, Transacao, Fornecedor, TipoPagamento
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.apps import apps

def obter_filiais(empresa):
    return Filial.objects.filter(empresa=empresa)

def obter_transacoes(empresa):
    return Transacao.objects.filter(empresa=empresa)

def obter_fornecedores(empresa):
    return Fornecedor.objects.filter(empresa=empresa)

def obter_tipos_pagamento(empresa):
    return TipoPagamento.objects.filter(empresa=empresa)

def obter_dados_selecionados(filial_id, transacao_id, fornecedor_id, tipo_pagamento_id):
    """Recebe IDs e retorna os objetos correspondentes"""
    filial = Filial.objects.get(id=filial_id)
    transacao = Transacao.objects.get(id=transacao_id)
    fornecedor = Fornecedor.objects.get(id=fornecedor_id)
    tipo_pagamento = TipoPagamento.objects.get(id=tipo_pagamento_id)
    return filial, transacao, fornecedor, tipo_pagamento

@login_required
def generic_autocomplete(request, model_name):
    q = request.GET.get('q', '')
    empresa = request.user.empresa

    try:
        Model = apps.get_model('financeiro', model_name)  # Substitua 'financeiro' se o app tiver outro nome
    except LookupError:
        return JsonResponse({'results': []})

    queryset = Model.objects.filter(empresa=empresa)
    
    if hasattr(Model, 'nome'):
        queryset = queryset.filter(nome__icontains=q)
    else:
        return JsonResponse({'results': []})

    results = [{'id': obj.id, 'text': obj.nome} for obj in queryset[:20]]
    return JsonResponse({'results': results})
