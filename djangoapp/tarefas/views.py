# tarefas/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from .models import Tarefa, HistoricoTarefa
from .forms import TarefaForm, FinalizarTarefaForm, RejeitarTarefaForm
from django.contrib.auth.decorators import user_passes_test
from django.db import models
from django.http import JsonResponse

def registrar_historico(tarefa, usuario, acao, obs=None):
    HistoricoTarefa.objects.create(tarefa=tarefa, usuario=usuario, acao=acao, observacao=obs)

def is_gestor(user):
    return user.groups.filter(name__in=['Gestor', 'Administrador']).exists()

def is_administrador(user):
    return user.groups.filter(name='Administrador').exists()

def is_colaborador(user):
    return user.groups.filter(name='Colaborador').exists()

@login_required
def listar_tarefas(request):
    user = request.user

    if is_administrador(user):
        # Admin vê tudo da empresa
        tarefas = Tarefa.objects.filter(empresa=user.empresa)
    elif is_gestor(user):
        # Gestor vê: suas tarefas + tarefas atribuídas a colaboradores da mesma empresa
        colaboradores = user.empresa.user_set.filter(groups__name='Colaborador')
        tarefas = Tarefa.objects.filter(
            empresa=user.empresa
        ).filter(
            models.Q(responsavel__in=colaboradores) |
            models.Q(responsavel=user) |
            models.Q(criado_por=user)
        )
    else:
        # Colaborador vê: tarefas atribuídas a ele ou criadas por ele
        tarefas = Tarefa.objects.filter(
            empresa=user.empresa
        ).filter(
            models.Q(responsavel=user) |
            models.Q(criado_por=user)
        )

    tarefas = tarefas.order_by('-data_execucao')
    return render(request, 'tarefas/listar.html', {'tarefas': tarefas})

@login_required
def criar_tarefa(request):
    if request.method == 'POST':
        form = TarefaForm(request.POST, user=request.user)
        if form.is_valid():
            tarefa = form.save(commit=False)
            tarefa.empresa = request.user.empresa
            tarefa.criado_por = request.user
            tarefa.save()
            registrar_historico(tarefa, request.user, 'CRIOU')
            messages.success(request, "Tarefa criada com sucesso.")
            return redirect('listar_tarefas')
    else:
        form = TarefaForm(user=request.user)
    return render(request, 'tarefas/form.html', {'form': form})

@login_required
def finalizar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id, responsavel=request.user)

    if tarefa.status not in ['pendente', 'rejeitado']:
        messages.warning(request, "Você não pode finalizar esta tarefa.")
        return redirect('listar_tarefas')

    if request.method == 'POST':
        form = FinalizarTarefaForm(request.POST)
        if form.is_valid():
            tarefa.status = 'finalizada'
            tarefa.data_finalizacao = timezone.now()
            tarefa.save()
            registrar_historico(tarefa, request.user, 'FINALIZADA', form.cleaned_data['observacao'])
            messages.success(request, "Tarefa finalizada com sucesso.")
            return redirect('listar_tarefas')
    else:
        form = FinalizarTarefaForm()

    return render(request, 'tarefas/finalizar.html', {'tarefa': tarefa, 'form': form})

@login_required
@user_passes_test(is_gestor)
def validar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    if request.user.is_staff:
        tarefa.status = 'validada'
        tarefa.data_validacao = timezone.now()
        tarefa.save()
        registrar_historico(tarefa, request.user, 'VALIDADA')
        messages.success(request, "Tarefa validada.")
    return redirect('listar_tarefas')

@login_required
def rejeitar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)

    if not request.user.groups.filter(name__in=['Gestor', 'Administrador']).exists():
        messages.error(request, "Você não tem permissão para rejeitar esta tarefa.")
        return redirect('listar_tarefas')

    if request.method == 'POST':
        form = RejeitarTarefaForm(request.POST)
        if form.is_valid():
            tarefa.status = 'REJEITADA'
            tarefa.save()
            registrar_historico(tarefa, request.user, 'rejeitou', form.cleaned_data['observacao'])
            messages.warning(request, "Tarefa rejeitada com observação.")
            return redirect('listar_tarefas')
    else:
        form = RejeitarTarefaForm()

    return render(request, 'tarefas/rejeitar.html', {'form': form, 'tarefa': tarefa})

@login_required
def historico_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    historico = tarefa.historico.order_by('-data')
    return render(request, 'tarefas/historico.html', {'tarefa': tarefa, 'historico': historico})

@login_required
def validar_execucao(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    if tarefa.criado_por != request.user:
        messages.error(request, "Apenas quem criou a tarefa pode validar a execução.")
        return redirect('listar_tarefas')

    tarefa.status = 'validado'
    tarefa.data_validacao = timezone.now()
    tarefa.save()
    registrar_historico(tarefa, request.user, 'validou')
    messages.success(request, "Tarefa validada com sucesso.")
    return redirect('listar_tarefas')

@login_required
def rejeitar_execucao(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)
    if tarefa.criado_por != request.user:
        messages.error(request, "Apenas quem criou a tarefa pode rejeitar a execução.")
        return redirect('listar_tarefas')

    if request.method == 'POST':
        form = RejeitarTarefaForm(request.POST)
        if form.is_valid():
            tarefa.status = 'rejeitado'
            tarefa.save()
            registrar_historico(tarefa, request.user, 'rejeitou', form.cleaned_data['observacao'])
            messages.warning(request, "Tarefa rejeitada e devolvida ao responsável.")
            return redirect('listar_tarefas')
    else:
        form = RejeitarTarefaForm()

    return render(request, 'tarefas/rejeitar_execucao.html', {'form': form, 'tarefa': tarefa})

@login_required
def marcar_tarefa_visualizada(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)

    if request.user == tarefa.responsavel:
        ja_viu = tarefa.historico.filter(usuario=request.user, acao='VISUALIZADO').exists()
        if not ja_viu:
            registrar_historico(tarefa, request.user, 'VISUALIZADO')
    return JsonResponse({'ok': True})
