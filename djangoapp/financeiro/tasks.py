# financeiro/tasks.py
from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from financeiro.models import ContaPagar, RelatorioFaturamentoMensal, Filial
from core.notificacoes import enviar_mensagem_telegram
from collections import defaultdict
from core.utils import formatar_brl
from accounts.models import Empresa
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
import os
import tempfile
import zipfile
import shutil
from django.core.files import File
from dateutil.relativedelta import relativedelta

User = get_user_model()

@shared_task(name="Verificar contas vencidas")
def notificar_contas_vencidas():
    hoje = now().date()

    for user in User.objects.filter(telegram_chat_id__isnull=False, ativo=True):
        contas = ContaPagar.objects.filter(
            empresa=user.empresa,
            status='vencida',
            valor_pago__lte=0
        )

        if not contas.exists():
            continue

        # Agrupamento por filial e fornecedor
        dados_agrupados = (
            contas
            .values('filial__nome', 'fornecedor__nome')
            .annotate(
                total=Sum('valor_bruto'),
                quantidade=Count('id')
            )
            .order_by('filial__nome', 'fornecedor__nome')
        )

        # Organiza em um dicionário por filial
        por_filial = defaultdict(list)
        for item in dados_agrupados:
            filial = item['filial__nome'] or "Filial não informada"
            fornecedor = item['fornecedor__nome'] or "Fornecedor não informado"
            total = item['total'] or 0
            quantidade = item['quantidade']
            por_filial[filial].append((fornecedor, total, quantidade))

        # Monta a mensagem
        mensagem = "━━━━━━━━━━━━━━━━━━━━━━\n"
        mensagem += f"📅 <b>{hoje.strftime('%d/%m/%Y')}</b>\n"
        mensagem += "<b>Contas Vencidas</b>\n"        
        mensagem += "━━━━━━━━━━━━━━━━━━━━━━\n"
        for filial, fornecedores in por_filial.items():
            mensagem += f"\n<b>{filial}</b>:\n"
            total_filial = 0
            qtd_filial = 0
            for fornecedor, total, quantidade in fornecedores:
                mensagem += f"• {fornecedor} - {formatar_brl(total)} - {quantidade} conta(s)\n"
                total_filial += total
                qtd_filial += quantidade
            mensagem += f"➡️ <b>Total: {formatar_brl(total_filial)} ({qtd_filial} conta(s))</b>\n"


        total_geral = contas.aggregate(total=Sum('valor_bruto'))['total'] or 0
        mensagem += f"\n<b>Total geral: {contas.count()} conta(s)</b>"
        mensagem += f"\n<b>Valor total: {formatar_brl(total_geral)}</b>"

        enviar_mensagem_telegram(user.telegram_chat_id, mensagem)

@shared_task(name="Verificar contas a vencer nos próximos 7 dias")
def notificar_contas_a_vencer():
    hoje = now().date()
    limite = hoje + timedelta(days=7)

    for user in User.objects.filter(telegram_chat_id__isnull=False, ativo=True):
        contas = ContaPagar.objects.filter(
            empresa=user.empresa,
            status='a_vencer',
            data_vencimento__gte=hoje,
            data_vencimento__lte=limite
        )

        if not contas.exists():
            continue

        # Agrupar por filial e fornecedor
        dados_agrupados = (
            contas
            .values('filial__nome', 'fornecedor__nome')
            .annotate(
                total=Sum('valor_bruto'),
                quantidade=Count('id')
            )
            .order_by('filial__nome', 'fornecedor__nome')
        )

        por_filial = defaultdict(list)
        for item in dados_agrupados:
            filial = item['filial__nome'] or "Filial não informada"
            fornecedor = item['fornecedor__nome'] or "Fornecedor não informado"
            total = item['total'] or 0
            quantidade = item['quantidade']
            por_filial[filial].append((fornecedor, total, quantidade))

        # Montar a mensagem
        mensagem = "━━━━━━━━━━━━━━━━━━━━━━\n"
        mensagem += f"📅 <b>{hoje.strftime('%d/%m/%Y')}</b>\n"
        mensagem += "<b>Contas a vencer nos próximos 7 dias</b>\n"
        mensagem += "━━━━━━━━━━━━━━━━━━━━━━\n"

        for filial, fornecedores in por_filial.items():
            mensagem += f"\n<b>{filial}</b>:\n"
            total_filial = 0
            qtd_filial = 0
            for fornecedor, total, quantidade in fornecedores:
                mensagem += f"• {fornecedor} - {formatar_brl(total)} - {quantidade} conta(s)\n"
                total_filial += total
                qtd_filial += quantidade
            mensagem += f"➡️ <b>Total: {formatar_brl(total_filial)} ({qtd_filial} conta(s))</b>\n"

        total_geral = contas.aggregate(total=Sum('valor_bruto'))['total'] or 0
        mensagem += f"\n<b>Total geral: {contas.count()} conta(s)</b>"
        mensagem += f"\n<b>Valor total: {formatar_brl(total_geral)}</b>"

        enviar_mensagem_telegram(user.telegram_chat_id, mensagem)

@shared_task(name="Atualizar status de contas vencidas")
def atualizar_status_contas():
    hoje = now().date()
    contas_a_vencer = ContaPagar.objects.filter(status='a_vencer', data_vencimento__lt=hoje)
    atualizadas = contas_a_vencer.update(status='vencida')
    return f"{atualizadas} contas atualizadas para 'vencida'"

def gerar_excel_filial(filial, contas, mes, ano):
    """Gera um arquivo Excel com as contas pagas de uma filial"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{filial.nome[:30]}"  # Limita o tamanho do nome da aba

    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")

    # Título
    ws.merge_cells('A1:M1')
    titulo_cell = ws['A1']
    titulo_cell.value = f"RELATÓRIO DE FATURAMENTO - {filial.nome}"
    titulo_cell.font = Font(bold=True, size=14)
    titulo_cell.alignment = Alignment(horizontal="center", vertical="center")

    # Subtítulo com período
    ws.merge_cells('A2:M2')
    subtitulo_cell = ws['A2']
    meses = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    subtitulo_cell.value = f"Período: {meses[mes]}/{ano}"
    subtitulo_cell.font = Font(bold=True, size=11)
    subtitulo_cell.alignment = Alignment(horizontal="center", vertical="center")

    # Linha em branco
    ws.append([])

    # Cabeçalhos
    headers = [
        'Filial', 'Banco Pagamento', 'Transação', 'Fornecedor', 'Documento',
        'Data Movimentação', 'Data Vencimento', 'Data Pagamento',
        'Valor Bruto', 'Juros', 'Multa', 'Valor Pago', 'Nº Notas'
    ]
    ws.append(headers)

    # Estiliza os cabeçalhos
    header_row = ws[4]
    for cell in header_row:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment

    # Dados
    total_valor_bruto = 0
    total_valor_pago = 0

    for conta in contas:
        ws.append([
            conta.filial.nome,
            conta.conta_bancaria_pagamento.nome if conta.conta_bancaria_pagamento else 'NÃO INFORMADO',
            conta.transacao.nome,
            conta.fornecedor.nome if conta.fornecedor else '',
            conta.documento,
            conta.data_movimentacao.strftime('%d/%m/%Y'),
            conta.data_vencimento.strftime('%d/%m/%Y'),
            conta.data_pagamento.strftime('%d/%m/%Y') if conta.data_pagamento else '',
            float(conta.valor_bruto),
            float(conta.valor_juros),
            float(conta.valor_multa),
            float(conta.valor_pago),
            conta.numero_notas,
        ])
        total_valor_bruto += conta.valor_bruto
        total_valor_pago += conta.valor_pago

    # Linha de totais
    ultima_linha = ws.max_row + 1
    ws.append([
        '', '', '', '', '', '', '', 'TOTAL:',
        float(total_valor_bruto), '', '', float(total_valor_pago), ''
    ])

    # Estiliza a linha de totais
    total_row = ws[ultima_linha]
    for cell in total_row:
        cell.font = Font(bold=True)
        if cell.column in [9, 12]:  # Colunas de valores
            cell.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

    # Ajusta largura das colunas
    column_widths = {
        'A': 20, 'B': 20, 'C': 20, 'D': 30, 'E': 15,
        'F': 18, 'G': 18, 'H': 18, 'I': 15, 'J': 10,
        'K': 10, 'L': 15, 'M': 20
    }
    for col, width in column_widths.items():
        ws.column_dimensions[col].width = width

    return wb

@shared_task(name="Gerar relatório de faturamento mensal")
def gerar_relatorio_faturamento_mensal(mes_ref=None, ano_ref=None):
    """
    Task que roda todo dia 1 de cada mês para gerar o relatório do mês anterior

    Args:
        mes_ref: Mês de referência (1-12). Se None, usa mês anterior
        ano_ref: Ano de referência. Se None, usa ano do mês anterior
    """
    hoje = now().date()

    if mes_ref and ano_ref:
        # Permite especificar mês/ano manualmente (útil para testes)
        mes = mes_ref
        ano = ano_ref
        print(f"[Relatório] Modo manual: gerando para {mes:02d}/{ano}")
    else:
        # Calcula o mês anterior
        mes_anterior = hoje - relativedelta(months=1)
        mes = mes_anterior.month
        ano = mes_anterior.year
        print(f"[Relatório] Modo automático: hoje={hoje}, gerando para {mes:02d}/{ano}")

    empresas = Empresa.objects.filter(ativo=True)
    print(f"[Relatório] Empresas ativas encontradas: {empresas.count()}")

    for empresa in empresas:
        try:
            print(f"\n[Relatório] Processando empresa: {empresa.nome} (ID={empresa.id})")

            # Busca contas pagas no mês anterior
            contas = ContaPagar.objects.filter(
                empresa=empresa,
                status='pago',
                data_pagamento__month=mes,
                data_pagamento__year=ano
            ).select_related('filial', 'conta_bancaria_pagamento', 'transacao', 'fornecedor')

            total_contas = contas.count()
            print(f"[Relatório] {empresa.nome}: {total_contas} contas pagas em {mes:02d}/{ano}")

            if total_contas > 0:
                # Mostra detalhes das primeiras contas
                print(f"[Relatório] Primeiras contas:")
                for c in contas[:3]:
                    print(f"  - ID={c.id}, Filial={c.filial.nome}, Data={c.data_pagamento}, Valor={c.valor_pago}")

            if not contas.exists():
                print(f"[Relatório] {empresa.nome}: Nenhuma conta paga, pulando geração")
                continue  # Pula se não houver contas pagas

            # Agrupa por filial
            filiais_com_contas = {}
            for conta in contas:
                filial = conta.filial
                if filial not in filiais_com_contas:
                    filiais_com_contas[filial] = []
                filiais_com_contas[filial].append(conta)

            print(f"[Relatório] Filiais com contas: {len(filiais_com_contas)}")
            for filial, contas_filial in filiais_com_contas.items():
                print(f"  - {filial.nome}: {len(contas_filial)} contas")

            # Cria diretório temporário para os arquivos Excel
            temp_dir = tempfile.mkdtemp()
            print(f"[Relatório] Diretório temporário criado: {temp_dir}")
            try:
                # Gera um arquivo Excel para cada filial
                for filial, contas_filial in filiais_com_contas.items():
                    # Nome seguro para a pasta
                    nome_pasta = filial.nome.replace('/', '-').replace('\\', '-')
                    pasta_filial = os.path.join(temp_dir, nome_pasta)
                    os.makedirs(pasta_filial, exist_ok=True)
                    print(f"[Relatório] Gerando Excel para {filial.nome}...")

                    # Gera o Excel
                    wb = gerar_excel_filial(filial, contas_filial, mes, ano)

                    # Salva o arquivo
                    arquivo_excel = os.path.join(pasta_filial, f'faturamento_{mes:02d}_{ano}.xlsx')
                    wb.save(arquivo_excel)
                    print(f"[Relatório] Excel salvo: {arquivo_excel}")

                # Cria o arquivo ZIP em um arquivo temporário
                zip_filename = f'relatorio_faturamento_{mes:02d}_{ano}_{empresa.nome.replace(" ", "_")}.zip'
                zip_temp_path = os.path.join(temp_dir, zip_filename)
                print(f"[Relatório] Criando ZIP: {zip_temp_path}")

                with zipfile.ZipFile(zip_temp_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    arquivos_adicionados = 0
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith('.xlsx'):
                                file_path = os.path.join(root, file)
                                # Mantém a estrutura de pastas dentro do ZIP
                                arcname = os.path.relpath(file_path, temp_dir)
                                zipf.write(file_path, arcname)
                                arquivos_adicionados += 1
                                print(f"[Relatório] Adicionado ao ZIP: {arcname}")

                print(f"[Relatório] ZIP criado com {arquivos_adicionados} arquivos")

                # Salva ou atualiza o relatório no banco de dados
                relatorio, created = RelatorioFaturamentoMensal.objects.update_or_create(
                    empresa=empresa,
                    mes=mes,
                    ano=ano,
                    defaults={'gerado_por': None}
                )
                print(f"[Relatório] Registro no DB: {'criado' if created else 'atualizado'} (ID={relatorio.id})")

                # Remove arquivo antigo do campo (OverwriteStorage vai substituir automaticamente)
                if relatorio.arquivo_zip:
                    print(f"[Relatório] Substituindo arquivo antigo: {relatorio.arquivo_zip.name}")

                # Anexa o arquivo ZIP - OverwriteStorage sobrescreve automaticamente
                print(f"[Relatório] Salvando arquivo no Django (com OverwriteStorage)...")
                with open(zip_temp_path, 'rb') as f:
                    relatorio.arquivo_zip.save(zip_filename, File(f), save=True)

                print(f"[Relatório] Arquivo salvo em: {relatorio.arquivo_zip.path}")
                print(f"[Relatório] ✅ Relatório gerado com sucesso para {empresa.nome}!")

            finally:
                # Limpa o diretório temporário
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            # Log do erro (você pode adicionar logging aqui)
            print(f"❌ ERRO ao gerar relatório para {empresa.nome}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n[Relatório] Processo finalizado!")
    return f"Relatórios gerados para {mes:02d}/{ano}"
