# financeiro/tasks.py
from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from financeiro.models import ContaPagar
from core.notificacoes import enviar_mensagem_telegram

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

        # Agrupar por filial e fornecedor
        agrupadas = (
            contas
            .values('filial__nome', 'fornecedor__nome')
            .annotate(
                total=Sum('valor_bruto'),
                quantidade=Count('id')
            )
            .order_by('filial__nome', 'fornecedor__nome')
        )

        mensagem = "🚨 <b>Contas Vencidas</b>\n"
        for item in agrupadas:
            filial = item['filial__nome'] or "Filial não informada"
            fornecedor = item['fornecedor__nome'] or "Fornecedor não informado"
            valor_total = item['total'] or 0
            quantidade = item['quantidade']
            mensagem += f"• {filial} - {fornecedor} - R$ {valor_total:.2f} - {quantidade} conta(s)\n"

        total_valor = contas.aggregate(total=Sum('valor_bruto'))['total'] or 0
        mensagem += f"\n<b>Total de contas: {contas.count()}</b>"
        mensagem += f"\n<b>Valor total: R$ {total_valor:.2f}</b>"

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
        ).order_by('data_vencimento')

        if not contas.exists():
            continue

        total_valor = contas.aggregate(total=Sum('valor_bruto'))['total'] or 0

        mensagem = f"📆 <b>Contas a vencer nos próximos 7 dias</b> \n"
        for conta in contas:
            mensagem += (
                f"• {conta.filial.nome} - {conta.fornecedor.nome} - "
                f"R$ {conta.valor_bruto} (vence em {conta.data_vencimento})\n"
            )

        mensagem += f"\n<b>Total de contas: {contas.count()}</b>"
        mensagem += f"\n<b>Valor total: R$ {total_valor:.2f}</b>"

        enviar_mensagem_telegram(user.telegram_chat_id, mensagem)
