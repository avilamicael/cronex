# Segurança dos Relatórios de Faturamento

## ✅ Proteções Implementadas

### 1. Controle de Acesso na View
```python
@login_required
@grupos_necessarios("Administrador", "Financeiro", "Gestor")
def download_relatorio_faturamento(request, relatorio_id):
```

**Proteções:**
- ✅ Requer autenticação (usuário logado)
- ✅ Requer grupo: Administrador, Financeiro ou Gestor
- ✅ Valida que o relatório pertence à empresa do usuário
- ✅ Retorna 404 se relatório não existir ou não pertencer à empresa
- ✅ Headers de segurança (`X-Content-Type-Options`, `Content-Type`)

### 2. Isolamento Multi-Tenant
```python
relatorio = get_object_or_404(
    RelatorioFaturamentoMensal,
    id=relatorio_id,
    empresa=request.user.empresa  # ← Filtro por empresa
)
```

**Proteções:**
- ✅ Usuário da Empresa A não pode baixar relatório da Empresa B
- ✅ Mesmo conhecendo o ID, o filtro por empresa bloqueia

### 3. Arquivo Servido via Django (não exposto diretamente)
```python
response = FileResponse(relatorio.arquivo_zip.open('rb'), as_attachment=True)
```

**Proteções:**
- ✅ Arquivo não acessível via URL direta como `/media/relatorios_faturamento/...`
- ✅ Passa obrigatoriamente pela validação da view

---

## ⚠️ IMPORTANTE: Configuração para Produção

### Problema: Acesso Direto aos Arquivos Media

Em **desenvolvimento**, o Django serve arquivos media automaticamente. Em **produção**, o Nginx/Apache normalmente serve arquivos estáticos e media **sem passar pelo Django**, o que pode expor os relatórios.

### 🔒 Solução: Proteger Diretório de Relatórios no Nginx

#### Opção 1: Bloquear Acesso Direto (Recomendado)

Adicione ao seu `nginx.conf`:

```nginx
server {
    # ... outras configurações ...

    # Bloqueia acesso direto aos relatórios
    location /media/relatorios_faturamento/ {
        deny all;
        return 404;
    }

    # Serve outros arquivos media normalmente
    location /media/ {
        alias /data/web/media/;
    }

    # ... outras configurações ...
}
```

**Resultado:**
- ❌ Acesso direto: `https://seusite.com/media/relatorios_faturamento/...` → 404
- ✅ Via Django: `https://seusite.com/financeiro/relatorio-faturamento/1/download/` → OK (com validação)

#### Opção 2: X-Accel-Redirect (Nginx Avançado)

Para melhor performance, use X-Accel-Redirect:

**1. Configure o Nginx:**
```nginx
server {
    # Protege acesso direto
    location /media/relatorios_faturamento/ {
        internal;  # Apenas requisições internas do Nginx
        alias /data/web/media/relatorios_faturamento/;
    }
}
```

**2. Atualize a view Django:**
```python
# Em financeiro/views.py
from django.http import HttpResponse

@login_required
@grupos_necessarios("Administrador", "Financeiro", "Gestor")
def download_relatorio_faturamento(request, relatorio_id):
    relatorio = get_object_or_404(
        RelatorioFaturamentoMensal,
        id=relatorio_id,
        empresa=request.user.empresa
    )

    if not relatorio.arquivo_zip:
        raise Http404("Arquivo não encontrado.")

    # Nginx serve o arquivo internamente (mais rápido)
    response = HttpResponse()
    response['X-Accel-Redirect'] = f'/media/{relatorio.arquivo_zip.name}'
    response['Content-Type'] = 'application/zip'
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(relatorio.arquivo_zip.name)}"'
    return response
```

**Vantagens:**
- ✅ Django valida permissões
- ✅ Nginx serve o arquivo (performance)
- ✅ Não expõe caminho direto

---

## 🧪 Como Testar a Segurança

### Teste 1: Usuário não autenticado
```bash
# Deve redirecionar para login
curl -I http://localhost:8000/financeiro/relatorio-faturamento/1/download/
# Esperado: 302 Redirect para /accounts/login/
```

### Teste 2: Usuário sem permissão
```bash
# Login como usuário SEM grupo Financeiro/Gestor/Administrador
# Acesse: /financeiro/relatorio-faturamento/1/download/
# Esperado: 403 Forbidden
```

### Teste 3: Usuário de outra empresa
```bash
# Login como Empresa B
# Tente acessar relatório da Empresa A: /financeiro/relatorio-faturamento/1/download/
# Esperado: 404 Not Found
```

### Teste 4: Acesso direto ao arquivo (PRODUÇÃO)
```bash
# Deve ser bloqueado pelo Nginx
curl -I https://seusite.com/media/relatorios_faturamento/2025/10/relatorio_faturamento_09_2025_Cronex.zip
# Esperado: 404 Not Found (ou 403 Forbidden)
```

---

## 📋 Checklist de Segurança

### Desenvolvimento (Docker)
- [x] `@login_required` na view
- [x] `@grupos_necessarios` na view
- [x] Filtro por empresa no query
- [x] Headers de segurança
- [ ] Configurar `X_FRAME_OPTIONS = 'DENY'` no settings.py (opcional)
- [ ] Configurar `SECURE_CONTENT_TYPE_NOSNIFF = True` no settings.py (opcional)

### Produção
- [ ] Bloquear acesso direto a `/media/relatorios_faturamento/` no Nginx
- [ ] Implementar X-Accel-Redirect (opcional, para performance)
- [ ] Testar acesso sem autenticação
- [ ] Testar acesso de usuário sem permissão
- [ ] Testar isolamento entre empresas
- [ ] Configurar HTTPS (SSL/TLS)
- [ ] Configurar `SECURE_SSL_REDIRECT = True`
- [ ] Configurar `SESSION_COOKIE_SECURE = True`
- [ ] Configurar `CSRF_COOKIE_SECURE = True`

---

## 🔐 Níveis de Segurança

### Nível Atual: **MÉDIO-ALTO** 🟡

**Desenvolvimento:** ✅ Seguro
- Acesso controlado via Django
- Validação de permissões
- Isolamento multi-tenant

**Produção (sem configuração Nginx):** ⚠️ Vulnerável
- Arquivos podem ser acessados diretamente se alguém descobrir o caminho

### Nível Recomendado: **ALTO** 🟢

**Com configuração Nginx:** ✅ Muito Seguro
- Acesso direto bloqueado
- Validação completa de permissões
- Isolamento garantido

---

## 📞 Suporte

Para mais informações sobre segurança em Django:
- https://docs.djangoproject.com/en/4.2/topics/security/
- https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

Para configuração do Nginx:
- https://www.nginx.com/resources/wiki/start/topics/examples/x-accel/
