# financeiro/tasks.py
from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from financeiro.models import ContaPagar
from core.notificacoes import enviar_mensagem_telegram
from collections import defaultdict
from core.utils import formatar_brl

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
