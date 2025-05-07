from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from .forms import UsuarioConfigForm

@login_required
def configuracoes_usuario(request):
    usuario = request.user

    if request.method == 'POST':
        form = UsuarioConfigForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dados atualizados com sucesso.')
            return redirect('configuracoes_usuario')
        else:
            messages.error(request, 'Erro ao atualizar seus dados.')
    else:
        form = UsuarioConfigForm(instance=usuario)

    return render(request, 'accounts/configuracoes_usuario.html', {
        'form': form,
    })
