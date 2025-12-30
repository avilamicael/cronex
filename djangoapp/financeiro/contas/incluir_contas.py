import csv, re
import xml.etree.ElementTree as ET
from decimal import Decimal
from datetime import datetime
from io import TextIOWrapper
from financeiro.models import Filial, Transacao, Fornecedor, TipoPagamento, ContaPagar
from financeiro.forms import BaixaFormSet
from django.contrib import messages
from django.shortcuts import render, redirect, get_list_or_404
from django.db import transaction
from django.utils.timezone import now
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.apps import apps
from django.utils.timezone import now

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

@login_required
def baixar_contas_pagar_bulk(request):
    empresa = request.user.empresa

    # ---------- PASSO 1: usuário acaba de clicar em "Baixar selecionadas" ----------
    if request.method == "GET":
        ids = request.GET.getlist("ids")  # retorna todos os valores marcados como lista
        if not ids:
            messages.warning(request, "Nenhuma conta selecionada.")
            return redirect("listar_contas_pagar")

        id_list = [int(i) for i in ids if i.isdigit()]
        contas = ContaPagar.objects.filter(
            empresa=empresa,
            id__in=id_list,
            status__in=["a_vencer", "vencida"]
        )

        if not contas.exists():
            messages.error(request, "Nenhuma das contas selecionadas está disponível para baixa. Verifique o status.")
            return redirect("listar_contas_pagar")

        # Cria o formset passando a empresa para cada formulário
        queryset = ContaPagar.objects.filter(id__in=id_list)
        formset = BaixaFormSet(queryset=queryset, form_kwargs={'empresa': empresa})

        # Inicializa o campo conta_bancaria_pagamento com a filial da conta
        for form, conta in zip(formset.forms, contas):
            if not form.instance.conta_bancaria_pagamento_id:
                form.initial['conta_bancaria_pagamento'] = conta.filial.id

        # Busca as filiais (bancos) disponíveis para seleção
        filiais = Filial.objects.filter(empresa=empresa)

        return render(
            request,
            "financeiro/contas/baixar_contas_pagar.html",
            {
                "formset": formset,
                "contas": contas,
                "filiais": filiais,
                "today": now().date(),
            }
        )

    # ---------- PASSO 2: usuário preencheu e submeteu o formset ----------
    formset = BaixaFormSet(request.POST, form_kwargs={'empresa': empresa})
    if formset.is_valid():
        with transaction.atomic():
            for form in formset:
                conta: ContaPagar = form.save(commit=False)

                if conta.status in ["pago", "cancelado"]:
                    messages.error(request, f"A conta {conta.id} não pode ser baixada pois já está {conta.get_status_display}.")
                    return redirect("listar_contas_pagar")

                # calcula o valor pago com base nos campos preenchidos (sem desconto e acréscimos)
                conta.valor_pago = (
                    conta.valor_bruto
                    + conta.valor_juros
                    + conta.valor_multa
                )
                conta.status = "pago"
                conta.save()
        messages.success(request, "Contas baixadas com sucesso.")
        return redirect("listar_contas_pagar")

    ids = [form.instance.id for form in formset.forms]
    contas = ContaPagar.objects.filter(id__in=ids, empresa=empresa)
    filiais = Filial.objects.filter(empresa=empresa)
    messages.error(request, "Preencha todos os campos obrigatórios antes de confirmar a baixa.")

    return render(
        request,
        "financeiro/contas/baixar_contas_pagar.html",
        {
            "formset": formset,
            "contas": contas,
            "filiais": filiais,
            "today": now().date(),
        }
    )

def _importar_csv(arquivo, request, empresa):
    try:
        dados = csv.DictReader(TextIOWrapper(arquivo.file, encoding='utf-8'))
        contas_criadas = 0

        for linha in dados:
            try:
                # Conversão de datas
                data_mov = datetime.strptime(linha['data_movimentacao'], '%d/%m/%Y').date()
                data_venc = datetime.strptime(linha['data_vencimento'], '%d/%m/%Y').date()

                # Limpeza de campos
                cnpj_filial = re.sub(r'[^0-9]', '', linha.get('cnpj_filial', '')).strip()
                nome_filial_csv = linha.get('nome_filial', '').strip() or cnpj_filial
                fornecedor_cnpj = re.sub(r'[^0-9]', '', linha.get('fornecedor_cnpj', '')).strip()
                fornecedor_nome = linha.get('fornecedor_nome', '').strip()
                transacao_nome = linha.get('transacao', '').strip()
                tipo_pagamento_nome = linha.get('tipo_pagamento', '').strip()
                documento = linha.get('documento', '').strip()
                descricao = linha.get('descricao', '').strip()
                numero_notas = re.sub(r'[^0-9,]', '', linha.get('numero_notas', ''))
                codigo_barras = re.sub(r'[^0-9.]', '', linha.get('codigo_barras', ''))
                valor_bruto_str = linha['valor_bruto'].replace('.', '').replace(',', '.')
                valor_bruto = Decimal(valor_bruto_str)

                # Buscar ou criar Filial
                filial, _ = Filial.objects.get_or_create(
                    empresa=empresa,
                    cnpj=cnpj_filial,
                    defaults={'nome': nome_filial_csv}
                )

                # Buscar ou criar Transação (case insensitive)
                transacao = Transacao.objects.filter(empresa=empresa, nome__iexact=transacao_nome).first()
                if not transacao:
                    transacao = Transacao.objects.create(empresa=empresa, nome=transacao_nome)

                # Buscar ou criar Tipo de Pagamento (case insensitive)
                tipo_pagamento = TipoPagamento.objects.filter(empresa=empresa, nome__iexact=tipo_pagamento_nome).first()
                if not tipo_pagamento:
                    tipo_pagamento = TipoPagamento.objects.create(empresa=empresa, nome=tipo_pagamento_nome)

                # Buscar ou criar Fornecedor com regras específicas
                fornecedor = None

                if fornecedor_cnpj:
                    fornecedor = Fornecedor.objects.filter(empresa=empresa, cnpj=fornecedor_cnpj).first()
                    if not fornecedor:
                        if not fornecedor_nome:
                            raise ValueError("Fornecedor com CNPJ informado mas nome vazio. Não é possível importar.")
                        
                        # ⚠ Verifica se já existe fornecedor com mesmo nome
                        fornecedor_existente_por_nome = Fornecedor.objects.filter(empresa=empresa, nome__iexact=fornecedor_nome).first()
                        if fornecedor_existente_por_nome:
                            fornecedor = fornecedor_existente_por_nome  # Evita duplicação
                        else:
                            fornecedor = Fornecedor.objects.create(
                                empresa=empresa,
                                cnpj=fornecedor_cnpj,
                                nome=fornecedor_nome
                            )
                elif fornecedor_nome:
                    fornecedor = Fornecedor.objects.filter(empresa=empresa, nome__iexact=fornecedor_nome).first()
                    if not fornecedor:
                        fornecedor = Fornecedor.objects.create(
                            empresa=empresa,
                            nome=fornecedor_nome,
                            cnpj=''
                        )
                else:
                    raise ValueError("Linha inválida: fornecedor sem CNPJ e sem nome. Não é possível importar.")


                # Criar Conta
                conta = ContaPagar(
                    empresa=empresa,
                    filial=filial,
                    transacao=transacao,
                    fornecedor=fornecedor,
                    tipo_pagamento=tipo_pagamento,
                    documento=documento,
                    data_movimentacao=data_mov,
                    data_vencimento=data_venc,
                    valor_bruto=valor_bruto,
                    descricao=descricao,
                    numero_notas=numero_notas,
                    codigo_barras=codigo_barras,
                    criado_por=request.user
                )
                conta.calcular_saldo()
                conta.status = 'vencida' if conta.data_vencimento < now().date() else 'a_vencer'
                conta.save()
                contas_criadas += 1
            except Exception as e:
                messages.warning(request, f"Erro na linha: {linha} | Erro: {e}")

        messages.success(request, f"{contas_criadas} contas importadas de {arquivo.name}")
    except Exception as e:
        messages.error(request, f"Erro ao processar o arquivo CSV {arquivo.name}: {e}")

def _importar_xml(arquivo, request, empresa):
    try:
        tree = ET.parse(arquivo)
        root = tree.getroot()
        ns = {'ns': 'http://www.portalfiscal.inf.br/nfe'}
        contas_criadas = 0

        emit = root.find('.//ns:emit', ns)
        dest = root.find('.//ns:dest', ns)
        ide = root.find('.//ns:ide', ns)
        cobr = root.find('.//ns:cobr', ns)
        infAdic = root.find('.//ns:infAdic/ns:infCpl', ns)

        # Dados do fornecedor (emitente)
        cnpj_emit = emit.find('ns:CNPJ', ns).text
        nome_emit = emit.find('ns:xNome', ns).text

        # Buscar fornecedor por CNPJ
        fornecedor = Fornecedor.objects.filter(empresa=empresa, cnpj=cnpj_emit).first()
        if not fornecedor:
            # Verifica se já existe fornecedor com mesmo nome (evita duplicação)
            fornecedor = Fornecedor.objects.filter(empresa=empresa, nome__iexact=nome_emit).first()
            if not fornecedor:
                # Só cria se não existir nem por CNPJ nem por nome
                fornecedor = Fornecedor.objects.create(
                    empresa=empresa,
                    cnpj=cnpj_emit,
                    nome=nome_emit
                )

        # Dados da filial (destinatário)
        cnpj_dest = dest.find('ns:CNPJ', ns).text
        nome_dest = dest.find('ns:xNome', ns).text

        # Buscar filial por CNPJ
        filial = Filial.objects.filter(empresa=empresa, cnpj=cnpj_dest).first()
        if not filial:
            # Verifica se já existe filial com mesmo nome (evita duplicação)
            filial = Filial.objects.filter(empresa=empresa, nome__iexact=nome_dest).first()
            if not filial:
                # Só cria se não existir nem por CNPJ nem por nome
                filial = Filial.objects.create(
                    empresa=empresa,
                    cnpj=cnpj_dest,
                    nome=nome_dest
                )

        # Documento e descrição
        numero_nf = ide.find('ns:nNF', ns).text
        descricao = infAdic.text if infAdic is not None else ''
        data_mov = datetime.strptime(ide.find('ns:dhEmi', ns).text[:10], "%Y-%m-%d").date()

        # Verifica se o arquivo ja foi importado
        if ContaPagar.objects.filter(empresa=empresa, fornecedor=fornecedor, numero_notas=numero_nf).exists():
            messages.warning(request, f"A nota fiscal {numero_nf} do fornecedor {fornecedor.nome} já foi importada.")
            return


        # Transação padrão
        transacao, _ = Transacao.objects.get_or_create(nome="IMPORTACAO XML", empresa=empresa)
        tipo_pagamento, _ = TipoPagamento.objects.get_or_create(nome="BOLETO", empresa=empresa)

        # Duplicatas
        duplicatas = root.findall('.//ns:dup', ns)
        if duplicatas:
            for dup in duplicatas:
                vencimento = datetime.strptime(dup.find('ns:dVenc', ns).text, "%Y-%m-%d").date()
                valor = Decimal(dup.find('ns:vDup', ns).text)
                conta = ContaPagar.objects.create(
                    empresa=empresa,
                    filial=filial,
                    fornecedor=fornecedor,
                    transacao=transacao,
                    tipo_pagamento=tipo_pagamento,
                    documento=numero_nf,
                    numero_notas=numero_nf,
                    descricao=descricao,
                    data_movimentacao=data_mov,
                    data_vencimento=vencimento,
                    valor_bruto=valor,
                    criado_por=request.user
                )
                conta.calcular_saldo()
                conta.status = 'vencida' if vencimento < now().date() else 'a_vencer'
                conta.save()
                contas_criadas += 1
        else:
            valor_nf = Decimal(root.find('.//ns:ICMSTot/ns:vNF', ns).text)
            conta = ContaPagar.objects.create(
                empresa=empresa,
                filial=filial,
                fornecedor=fornecedor,
                transacao=transacao,
                tipo_pagamento=tipo_pagamento,
                documento=numero_nf,
                numero_notas=numero_nf,
                descricao=descricao,
                data_movimentacao=data_mov,
                data_vencimento=data_mov,
                valor_bruto=valor_nf,
                criado_por=request.user
            )
            conta.calcular_saldo()
            conta.status = 'vencida' if conta.data_vencimento < now().date() else 'a_vencer'
            conta.save()
            contas_criadas += 1

        messages.success(request, f"{contas_criadas} contas importadas do arquivo {arquivo.name}.")
    except Exception as e:
        messages.error(request, f"Erro ao importar {arquivo.name}: {e}")
