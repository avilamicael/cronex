# core/decorators.py

from django.http import HttpResponseForbidden
from functools import wraps

def grupos_necessarios(*nomes_grupos):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.groups.filter(name__in=nomes_grupos).exists():
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Você não tem permissão para acessar esta página.")
        return _wrapped_view
    return decorator
