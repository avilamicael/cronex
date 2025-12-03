"""
Views para gestão de certificados digitais e notas fiscais eletrônicas.
"""
import os
import zipfile
from datetime import datetime, timedelta
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Q
from django.core.files.base import ContentFile
from django.utils import timezone

from core.decorators import grupos_necessarios
from financeiro.models import CertificadoDigital, NotaFiscal, Filial
from financeiro.crypto import decrypt_password
from .forms import CertificadoDigitalForm, ConsultaNFeForm, FiltroNotasFiscaisForm
from .sefaz_client import SefazClient


# ========================================
# GESTÃO DE CERTIFICADOS DIGITAIS
# ========================================

@grupos_necessarios("Administrador", "Financeiro")
def certificados_lista(request):
    """Lista todos os certificados da empresa"""
    from financeiro.models import ConfiguracaoNFe

    empresa = request.user.empresa
    certificados = CertificadoDigital.objects.filter(empresa=empresa).select_related('filial')

    # Adiciona informação de configuração para cada certificado
    for cert in certificados:
        try:
            cert.config = cert.configuracao_nfe
        except ConfiguracaoNFe.DoesNotExist:
            cert.config = None

    context = {
        'certificados': certificados,
    }
    return render(request, 'financeiro/nfe/certificados_lista.html', context)


@grupos_necessarios("Administrador", "Financeiro")
def certificado_adicionar(request):
    """Adiciona um novo certificado"""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = CertificadoDigitalForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            certificado = form.save(commit=False)
            certificado.empresa = empresa
            certificado.criado_por = request.user
            certificado.save()

            messages.success(request, 'Certificado digital cadastrado com sucesso!')
            return redirect('certificados_lista')
    else:
        form = CertificadoDigitalForm(empresa=empresa)

    context = {
        'form': form,
        'titulo': 'Adicionar Certificado Digital'
    }
    return render(request, 'financeiro/nfe/certificado_form.html', context)


@grupos_necessarios("Administrador", "Financeiro")
def certificado_editar(request, pk):
    """Edita um certificado existente"""
    empresa = request.user.empresa
    certificado = get_object_or_404(CertificadoDigital, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = CertificadoDigitalForm(request.POST, request.FILES, instance=certificado, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Certificado atualizado com sucesso!')
            return redirect('certificados_lista')
    else:
        form = CertificadoDigitalForm(instance=certificado, empresa=empresa)

    context = {
        'form': form,
        'certificado': certificado,
        'titulo': 'Editar Certificado Digital'
    }
    return render(request, 'financeiro/nfe/certificado_form.html', context)


@grupos_necessarios("Administrador", "Financeiro")
def certificado_resetar_nsu(request, pk):
    """Reseta o NSU de um certificado para buscar tudo novamente"""
    empresa = request.user.empresa
    certificado = get_object_or_404(CertificadoDigital, pk=pk, empresa=empresa)

    if request.method == 'POST':
        certificado.ultimo_nsu = '000000000000000'
        certificado.save(update_fields=['ultimo_nsu'])
        messages.success(request, f'NSU do certificado {certificado.filial.nome} resetado com sucesso!')
        return redirect('certificados_lista')

    context = {
        'certificado': certificado,
    }
    return render(request, 'financeiro/nfe/certificado_resetar_nsu.html', context)


@grupos_necessarios("Administrador", "Financeiro")
def certificado_sincronizar_nsu(request, pk):
    """Sincroniza o NSU do certificado com a SEFAZ"""
    empresa = request.user.empresa
    certificado = get_object_or_404(CertificadoDigital, pk=pk, empresa=empresa)

    if request.method == 'POST':
        try:
            # Descriptografa a senha
            senha = decrypt_password(certificado.senha_encrypted)

            # Inicializa cliente SEFAZ
            client = SefazClient(
                certificado_path=certificado.arquivo_pfx.path,
                certificado_senha=senha,
                cnpj=certificado.filial.cnpj,
                uf_cod=certificado.uf_codigo
            )

            # Sincroniza NSU
            ult_nsu, max_nsu, mensagem = client.sincronizar_nsu()

            # Atualiza certificado
            nsu_anterior = certificado.ultimo_nsu
            certificado.ultimo_nsu = ult_nsu
            certificado.save(update_fields=['ultimo_nsu'])

            messages.success(
                request,
                f'NSU sincronizado com sucesso! '
                f'NSU anterior: {nsu_anterior} → NSU atual: {ult_nsu} '
                f'(Máximo: {max_nsu})'
            )

        except Exception as e:
            import traceback
            messages.error(request, f'Erro ao sincronizar NSU: {str(e)}')
            print(f"ERRO DETALHADO: {traceback.format_exc()}")

        return redirect('certificados_lista')

    context = {
        'certificado': certificado,
    }
    return render(request, 'financeiro/nfe/certificado_sincronizar_nsu.html', context)


@grupos_necessarios("Administrador", "Financeiro")
def certificado_deletar(request, pk):
    """Deleta um certificado"""
    empresa = request.user.empresa
    certificado = get_object_or_404(CertificadoDigital, pk=pk, empresa=empresa)

    if request.method == 'POST':
        filial_nome = certificado.filial.nome
        certificado.delete()
        messages.success(request, f'Certificado de {filial_nome} removido com sucesso!')
        return redirect('certificados_lista')

    context = {
        'certificado': certificado,
    }
    return render(request, 'financeiro/nfe/certificado_confirmar_delete.html', context)


# ========================================
# CONSULTA DE NOTAS FISCAIS NA SEFAZ
# ========================================

@grupos_necessarios("Administrador", "Financeiro")
def nfe_consultar(request):
    """Consulta NF-e na SEFAZ"""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = ConsultaNFeForm(request.POST, empresa=empresa)
        if form.is_valid():
            try:
                # Obtém dados do form
                certificado = form.cleaned_data['certificado']
                data_inicio = form.cleaned_data['data_inicio']
                data_fim = form.cleaned_data['data_fim']
                buscar_novos = form.cleaned_data['buscar_novos']

                # Descriptografa a senha
                senha = decrypt_password(certificado.senha_encrypted)

                # Inicializa cliente SEFAZ
                client = SefazClient(
                    certificado_path=certificado.arquivo_pfx.path,
                    certificado_senha=senha,
                    cnpj=certificado.filial.cnpj,
                    uf_cod=certificado.uf_codigo
                )

                # Busca documentos
                nsu_inicial = certificado.ultimo_nsu if buscar_novos else "000000000000000"

                if buscar_novos and nsu_inicial != "000000000000000":
                    messages.info(request, f'Buscando novos documentos desde NSU {nsu_inicial}...')
                else:
                    messages.info(request, 'Iniciando consulta completa na SEFAZ...')

                # Debug: mostra informações da consulta
                print(f"=== DEBUG CONSULTA SEFAZ ===")
                print(f"CNPJ: {certificado.filial.cnpj}")
                print(f"UF: {certificado.uf_codigo} ({certificado.get_uf_codigo_display()})")
                print(f"NSU Inicial: {nsu_inicial}")
                print(f"Certificado: {certificado.arquivo_pfx.path}")
                print(f"URL SEFAZ: {client.url}")

                # Variáveis para armazenar NSUs retornados
                ult_nsu = None
                max_nsu = None

                try:
                    # Faz uma consulta para obter o NSU atual
                    resposta_xml = client.consultar_dfe(nsu_inicial)
                    docs_temp, ult_nsu, max_nsu, mensagem = client.extrair_documentos(resposta_xml)

                    # Verifica se é erro de consumo indevido
                    if "Consumo Indevido" in (mensagem or ""):
                        # Atualiza o NSU do certificado se retornado
                        if ult_nsu:
                            nsu_anterior = certificado.ultimo_nsu
                            certificado.ultimo_nsu = ult_nsu
                            certificado.save(update_fields=['ultimo_nsu'])

                            messages.error(
                                request,
                                'A SEFAZ bloqueou a consulta por consumo indevido (erro 656). '
                                'Isso acontece quando você tenta fazer múltiplas consultas em um curto período de tempo.'
                            )
                            messages.info(
                                request,
                                f'NSU atualizado automaticamente: {nsu_anterior} → {ult_nsu}. '
                                'Aguarde alguns minutos antes de tentar novamente, ou use a opção "Buscar novos documentos".'
                            )
                        else:
                            messages.error(
                                request,
                                'A SEFAZ bloqueou a consulta por consumo indevido. '
                                'Aguarde 1 hora antes de tentar novamente. '
                                'Se o problema persistir, use o botão "Sincronizar NSU" na lista de certificados.'
                            )
                        return redirect('nfe_consultar')

                    # Busca todos os documentos
                    documentos = client.buscar_todos_documentos(nsu_inicial)

                except Exception as e:
                    if "Consumo Indevido" in str(e) or "656" in str(e):
                        messages.error(
                            request,
                            'A SEFAZ bloqueou a consulta por consumo indevido (erro 656). '
                            'Aguarde alguns minutos antes de tentar novamente.'
                        )
                        messages.info(
                            request,
                            'Dica: Use o botão "Sincronizar NSU" na lista de certificados para atualizar o NSU sem fazer consultas completas.'
                        )
                    else:
                        raise e
                    return redirect('nfe_consultar')

                print(f"Total de documentos retornados: {len(documentos)}")
                print(f"===========================")

                if not documentos:
                    # Atualiza NSU mesmo sem documentos
                    if ult_nsu:
                        certificado.ultimo_nsu = ult_nsu
                        certificado.save(update_fields=['ultimo_nsu'])

                    if buscar_novos and nsu_inicial != "000000000000000":
                        messages.warning(request, f'Nenhum documento novo desde o NSU {nsu_inicial}.')
                    else:
                        messages.warning(request, 'Nenhum documento encontrado na SEFAZ para este CNPJ no momento.')
                    return redirect('nfe_consultar')

                # Filtra por período
                documentos_filtrados = client.filtrar_por_periodo(
                    documentos,
                    datetime.combine(data_inicio, datetime.min.time()),
                    datetime.combine(data_fim, datetime.max.time())
                )

                if not documentos_filtrados:
                    messages.warning(request, f'Nenhuma nota encontrada no período {data_inicio} a {data_fim}.')
                    return redirect('nfe_consultar')

                # Importa documentos para o banco
                importados = 0
                duplicados = 0

                with transaction.atomic():
                    for xml in documentos_filtrados:
                        # Verifica se é resumo e busca XML completo
                        xml_final = xml
                        if client.eh_resumo_nfe(xml):
                            chave = client.extrair_chave_resumo(xml)
                            if chave:
                                print(f"Detectado resumo, buscando XML completo para: {chave}")
                                xml_completo = client.buscar_xml_completo(chave)
                                if xml_completo:
                                    xml_final = xml_completo
                                    print(f"XML completo obtido para: {chave}")
                                else:
                                    print(f"Não foi possível obter XML completo, usando resumo: {chave}")

                        metadados = client.extrair_metadados_nfe(xml_final)

                        # Verifica se já existe
                        if NotaFiscal.objects.filter(chave_acesso=metadados['chave_acesso']).exists():
                            duplicados += 1
                            continue

                        # Cria registro
                        nota = NotaFiscal(
                            empresa=empresa,
                            filial=certificado.filial,
                            chave_acesso=metadados['chave_acesso'],
                            numero=metadados['numero'],
                            serie=metadados['serie'],
                            data_emissao=metadados['data_emissao'],
                            emitente_cnpj=metadados['emitente_cnpj'],
                            emitente_nome=metadados['emitente_nome'],
                            valor_total=metadados['valor_total'],
                            valor_desconto=metadados['valor_desconto'],
                            valor_liquido=metadados['valor_liquido'],
                            nsu=metadados['nsu'],
                            importado_por=request.user
                        )

                        # Salva XML (completo se conseguiu buscar, resumo caso contrário)
                        xml_bytes = client.xml_to_string(xml_final)
                        nota.arquivo_xml.save(
                            f"nfe_{metadados['chave_acesso']}.xml",
                            ContentFile(xml_bytes),
                            save=False
                        )

                        nota.save()
                        importados += 1

                    # Atualiza último NSU do certificado
                    # O ultNSU correto já foi retornado pela função extrair_documentos
                    if ult_nsu:
                        certificado.ultimo_nsu = ult_nsu
                        certificado.save(update_fields=['ultimo_nsu'])

                # Mensagem de sucesso
                msg = f'{importados} nota(s) importada(s) com sucesso!'
                if duplicados > 0:
                    msg += f' ({duplicados} já existente(s))'
                messages.success(request, msg)

                return redirect('nfe_lista')

            except Exception as e:
                import traceback
                messages.error(request, f'Erro ao consultar SEFAZ: {str(e)}')
                print(f"ERRO DETALHADO: {traceback.format_exc()}")
        else:
            # Form inválido - mostra os erros
            messages.error(request, 'Por favor, corrija os erros no formulário.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

    else:
        # Define período padrão (últimos 30 dias)
        data_fim = timezone.now().date()
        data_inicio = data_fim - timedelta(days=30)

        form = ConsultaNFeForm(
            initial={'data_inicio': data_inicio, 'data_fim': data_fim},
            empresa=empresa
        )

    context = {
        'form': form,
    }
    return render(request, 'financeiro/nfe/nfe_consultar.html', context)


# ========================================
# GESTÃO DE NOTAS FISCAIS IMPORTADAS
# ========================================

@grupos_necessarios("Administrador", "Financeiro")
def nfe_lista(request):
    """Lista notas fiscais importadas"""
    empresa = request.user.empresa

    # Filtros
    filtro_form = FiltroNotasFiscaisForm(request.GET or None, empresa=empresa)

    # Query base
    notas = NotaFiscal.objects.filter(empresa=empresa).select_related('filial', 'conta_pagar')

    # Aplica filtros
    if filtro_form.is_valid():
        # Filtro de filial
        filial = filtro_form.cleaned_data.get('filial')
        if filial:
            notas = notas.filter(filial=filial)

        # Filtro de período
        periodo = filtro_form.cleaned_data.get('periodo')
        if periodo:
            hoje = timezone.now().date()

            if periodo == 'hoje':
                notas = notas.filter(data_emissao__date=hoje)
            elif periodo == '7dias':
                data_inicio = hoje - timedelta(days=7)
                notas = notas.filter(data_emissao__date__gte=data_inicio)
            elif periodo == '30dias':
                data_inicio = hoje - timedelta(days=30)
                notas = notas.filter(data_emissao__date__gte=data_inicio)
            elif periodo == 'mes_atual':
                notas = notas.filter(
                    data_emissao__year=hoje.year,
                    data_emissao__month=hoje.month
                )
            elif periodo == 'mes_anterior':
                primeiro_dia_mes = hoje.replace(day=1)
                ultimo_dia_mes_anterior = primeiro_dia_mes - timedelta(days=1)
                notas = notas.filter(
                    data_emissao__year=ultimo_dia_mes_anterior.year,
                    data_emissao__month=ultimo_dia_mes_anterior.month
                )
            elif periodo == 'personalizado':
                data_inicio = filtro_form.cleaned_data.get('data_inicio')
                data_fim = filtro_form.cleaned_data.get('data_fim')
                if data_inicio:
                    notas = notas.filter(data_emissao__date__gte=data_inicio)
                if data_fim:
                    notas = notas.filter(data_emissao__date__lte=data_fim)

        # Filtro de status
        status = filtro_form.cleaned_data.get('status')
        if status:
            notas = notas.filter(status=status)

        # Filtro de emitente
        emitente = filtro_form.cleaned_data.get('emitente')
        if emitente:
            notas = notas.filter(
                Q(emitente_nome__icontains=emitente) |
                Q(emitente_cnpj__icontains=emitente.replace('.', '').replace('/', '').replace('-', ''))
            )

    # Ordenação
    notas = notas.order_by('-data_emissao')

    context = {
        'notas': notas,
        'filtro_form': filtro_form,
    }
    return render(request, 'financeiro/nfe/nfe_lista.html', context)


@grupos_necessarios("Administrador", "Financeiro")
def nfe_detalhes(request, pk):
    """Exibe detalhes de uma nota fiscal"""
    empresa = request.user.empresa
    nota = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    context = {
        'nota': nota,
    }
    return render(request, 'financeiro/nfe/nfe_detalhes.html', context)


# ========================================
# DOWNLOAD DE XMLs
# ========================================

@grupos_necessarios("Administrador", "Financeiro")
def nfe_download_xml(request, pk):
    """Download do XML de uma nota fiscal"""
    empresa = request.user.empresa
    nota = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if not nota.arquivo_xml:
        messages.error(request, 'Arquivo XML não disponível.')
        return redirect('nfe_detalhes', pk=pk)

    # Lê o arquivo
    xml_content = nota.arquivo_xml.read()
    filename = f"nfe_{nota.chave_acesso}.xml"

    # Retorna como download
    response = HttpResponse(xml_content, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


@grupos_necessarios("Administrador", "Financeiro")
def nfe_download_massa(request):
    """Download em massa de XMLs (ZIP)"""
    empresa = request.user.empresa

    # Obtém IDs das notas selecionadas
    nota_ids = request.GET.getlist('notas')

    if not nota_ids:
        messages.error(request, 'Nenhuma nota selecionada.')
        return redirect('nfe_lista')

    # Busca notas
    notas = NotaFiscal.objects.filter(id__in=nota_ids, empresa=empresa)

    if not notas.exists():
        messages.error(request, 'Notas não encontradas.')
        return redirect('nfe_lista')

    # Cria arquivo ZIP em memória
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for nota in notas:
            if nota.arquivo_xml:
                # Lê conteúdo do XML
                xml_content = nota.arquivo_xml.read()
                filename = f"nfe_{nota.chave_acesso}.xml"

                # Adiciona ao ZIP
                zip_file.writestr(filename, xml_content)

    # Prepara resposta
    zip_buffer.seek(0)
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"nfe_lote_{timestamp}.zip"

    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

    return response


@grupos_necessarios("Administrador", "Financeiro")
def nfe_deletar(request, pk):
    """Deleta uma nota fiscal"""
    empresa = request.user.empresa
    nota = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if request.method == 'POST':
        chave = nota.chave_acesso
        nota.delete()
        messages.success(request, f'Nota {chave} removida com sucesso!')
        return redirect('nfe_lista')

    context = {
        'nota': nota,
    }
    return render(request, 'financeiro/nfe/nfe_confirmar_delete.html', context)


# ========================================
# MONITORAMENTO DE IMPORTAÇÕES
# ========================================

@grupos_necessarios("Administrador", "Financeiro")
def nfe_status_importacao(request):
    """Exibe status das importações automáticas"""
    from financeiro.models import ConfiguracaoNFe

    empresa = request.user.empresa

    # Busca todas as configurações da empresa
    configs = ConfiguracaoNFe.objects.filter(
        certificado__empresa=empresa
    ).select_related('certificado', 'certificado__filial').order_by('certificado__filial__nome')

    context = {
        'configs': configs,
    }
    return render(request, 'financeiro/nfe/nfe_status_importacao.html', context)


@grupos_necessarios("Administrador", "Financeiro")
def nfe_ativar_busca_automatica(request, config_id):
    """Ativa/desativa busca automática para um certificado"""
    from financeiro.models import ConfiguracaoNFe

    empresa = request.user.empresa
    config = get_object_or_404(
        ConfiguracaoNFe,
        id=config_id,
        certificado__empresa=empresa
    )

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'ativar':
            config.busca_automatica_ativa = True
            config.save()
            messages.success(request, f'Busca automática ativada para {config.certificado.filial.nome}')
        elif acao == 'desativar':
            config.busca_automatica_ativa = False
            config.save()
            messages.success(request, f'Busca automática desativada para {config.certificado.filial.nome}')
        elif acao == 'ativar_historico':
            config.busca_historica_ativa = True
            config.busca_historica_status = 'ativa'
            config.save()
            messages.success(request, f'Busca histórica ativada para {config.certificado.filial.nome}')
        elif acao == 'desativar_historico':
            config.busca_historica_ativa = False
            config.busca_historica_status = 'inativa'
            config.save()
            messages.success(request, f'Busca histórica desativada para {config.certificado.filial.nome}')

    return redirect('nfe_status_importacao')


@grupos_necessarios("Administrador", "Financeiro")
def nfe_criar_configuracao(request, certificado_id):
    """Cria configuração automática para um certificado"""
    from financeiro.models import ConfiguracaoNFe, CertificadoDigital

    empresa = request.user.empresa
    certificado = get_object_or_404(
        CertificadoDigital,
        id=certificado_id,
        empresa=empresa
    )

    # Cria configuração se não existir
    config, created = ConfiguracaoNFe.objects.get_or_create(
        certificado=certificado
    )

    if created:
        messages.success(request, f'Configuração criada para {certificado.filial.nome}')
    else:
        messages.info(request, f'Configuração já existe para {certificado.filial.nome}')

    return redirect('nfe_status_importacao')
