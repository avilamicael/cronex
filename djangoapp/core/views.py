from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from financeiro.models import Filial

@login_required
def dashboard_view(request):
    return render(request, 'dashboard.html')

@login_required
@require_POST
def definir_filial_padrao(request):
    filial_id = request.POST.get('filial_padrao')
    if filial_id:
        try:
            filial = Filial.objects.get(id=filial_id, empresa=request.user.empresa)
            request.session['filial_padrao'] = filial.id
        except Filial.DoesNotExist:
            pass  # ignora se não existir
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
