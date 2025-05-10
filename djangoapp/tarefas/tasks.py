# tarefas/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Tarefa
from core.notificacoes import enviar_mensagem_telegram


def get_notificacao_texto(tarefa):
    return f"⚠️ Tarefa próxima do vencimento: {tarefa.titulo} às {tarefa.data_execucao.strftime('%d/%m/%Y %H:%M')}"

@shared_task(name="Verificar tarefas à vencer")
def verificar_tarefas_a_vencer():
    agora = timezone.now()
    tarefas = Tarefa.objects.filter(
        data_para_notificar__lte=agora,
        data_execucao__gte=agora
    )

    for tarefa in tarefas:
        mensagem = get_notificacao_texto(tarefa)
        responsavel = tarefa.responsavel

        if responsavel and responsavel.telegram_chat_id:
            enviar_mensagem_telegram(responsavel.telegram_chat_id, mensagem)

        gestores = tarefa.empresa.user_set.filter(groups__name='Gestor', receber_notificacoes_de_subordinados=True)
        for gestor in gestores:
            if gestor != responsavel and gestor.telegram_chat_id:
                enviar_mensagem_telegram(gestor.telegram_chat_id, mensagem)

        administradores = tarefa.empresa.user_set.filter(groups__name='Administrador', receber_notificacoes_de_subordinados=True)
        for admin in administradores:
            if admin != responsavel and admin.telegram_chat_id:
                enviar_mensagem_telegram(admin.telegram_chat_id, mensagem)

        tarefa.save()


@shared_task(name="Verificar tarefas vencidas")
def verificar_tarefas_vencidas():
    agora = timezone.now()
    tarefas_vencidas = Tarefa.objects.filter(
        data_execucao__lt=agora,
        status__in=['pendente', 'rejeitado']
    )

    for tarefa in tarefas_vencidas:
        mensagem = f"⏰ Tarefa VENCIDA: {tarefa.titulo} (vencia em {tarefa.data_execucao.strftime('%d/%m/%Y %H:%M')})"
        responsavel = tarefa.responsavel

        if responsavel and responsavel.telegram_chat_id:
            enviar_mensagem_telegram(responsavel.telegram_chat_id, mensagem)

        gestores = tarefa.empresa.user_set.filter(groups__name='Gestor', receber_notificacoes_de_subordinados=True)
        for gestor in gestores:
            if gestor != responsavel and gestor.telegram_chat_id:
                enviar_mensagem_telegram(gestor.telegram_chat_id, mensagem)

        administradores = tarefa.empresa.user_set.filter(groups__name='Administrador', receber_notificacoes_de_subordinados=True)
        for admin in administradores:
            if admin != responsavel and admin.telegram_chat_id:
                enviar_mensagem_telegram(admin.telegram_chat_id, mensagem)
