from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from .forms import UsuarioConfigForm
from django.contrib.auth import update_session_auth_hash
from accounts.forms import UsuarioSenhaForm

@login_required
def configuracoes_usuario(request):
    usuario = request.user

    if request.method == 'POST':
        form = UsuarioConfigForm(request.POST, instance=usuario)
        senha_form = UsuarioSenhaForm(user=usuario, data=request.POST)

        if form.is_valid() and not senha_form.is_valid():
            form.save()
            messages.success(request, 'Dados atualizados com sucesso.')
            return redirect('configuracoes_usuario')

        if senha_form.is_valid():
            senha_form.save()
            update_session_auth_hash(request, senha_form.user)  # mantém o usuário logado
            messages.success(request, 'Senha alterada com sucesso.')
            return redirect('configuracoes_usuario')

        messages.error(request, 'Erro ao salvar alterações.')
    else:
        form = UsuarioConfigForm(instance=usuario)
        senha_form = UsuarioSenhaForm(user=usuario)

    return render(request, 'accounts/configuracoes_usuario.html', {
        'form': form,
        'senha_form': senha_form,
    })
