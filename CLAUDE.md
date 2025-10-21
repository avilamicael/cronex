# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cronex is a Django-based financial management system focused on accounts payable ("contas a pagar"), built for multi-tenant use with company-based isolation. The system includes automated task scheduling, OFX file reconciliation, and Telegram notifications.

## Development Commands

### Docker-based Development (Recommended)
```bash
# Start all services (Django, PostgreSQL, Redis, Celery, Celery Beat, Adminer)
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f djangoapp
docker-compose logs -f celery

# Stop all services
docker-compose down

# Rebuild containers after dependency changes
docker-compose build
docker-compose up
```

### Local Development (with venv)
```bash
# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
cd djangoapp
pip install -r requirements.txt

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Run development server
python manage.py runserver

# Run Celery worker (separate terminal)
celery -A project worker -l info

# Run Celery Beat scheduler (separate terminal)
celery -A project beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Testing & Utilities
```bash
# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Access database via Adminer
# When using docker-compose: http://localhost:8080
# Server: psql, credentials from .env file
```

## Architecture

### Multi-Tenant Design
The entire application is built around multi-tenancy with company-level data isolation:
- **Empresa** (Company) is the central tenant model
- **User** model has ForeignKey to Empresa
- All financial data (Filial, Fornecedor, Transacao, ContaPagar) is scoped to Empresa
- Views filter all queries by `request.user.empresa`
- Forms are initialized with `empresa=empresa` parameter to scope related field queries

### Django Apps Structure

**accounts** - Authentication and multi-tenant foundation
- Custom User model extending AbstractUser
- Empresa (Company) model for tenant isolation
- User groups: Administrador, Gestor, Financeiro

**financeiro** - Core financial management
- Models: Filial, Fornecedor, Transacao, TipoPagamento, ContaPagar
- CSV/XML import functionality in `financeiro/contas/incluir_contas.py`
- OFX reconciliation: upload OFX files and match against paid accounts
- Status workflow: 'a_vencer' → 'vencida' (auto-updated via Celery) → 'pago' → 'cancelado'
- ContaPagar calculates `valor_saldo` automatically on save

**tarefas** - Task management with notifications
- Task assignment and tracking
- Telegram notifications for task deadlines

**core** - Shared utilities
- `decorators.py`: `@grupos_necessarios()` for role-based access control
- `notificacoes.py`: Telegram integration
- `utils.py`: Brazilian currency formatting

**project** - Django settings and configuration
- Settings use environment variables from `dotenv_files/.env`
- Celery configuration with Redis broker
- Brazilian locale (pt-br, America/Sao_Paulo)
- Custom AUTH_USER_MODEL = 'accounts.User'

### Celery Task System
Scheduled tasks are managed through django-celery-beat (configure via Django admin):

**financeiro.tasks**
- `notificar_contas_vencidas`: Daily alerts for overdue accounts grouped by Filial/Fornecedor
- `notificar_contas_a_vencer`: Weekly alerts for accounts due in next 7 days
- `atualizar_status_contas`: Auto-updates ContaPagar status from 'a_vencer' to 'vencida'

**tarefas.tasks**
- `verificar_tarefas_a_vencer`: Notify users before task deadlines
- `verificar_tarefas_vencidas`: Alert about overdue tasks
- Notifications sent to task owner + Gestores/Administradores if configured

### Docker Architecture
Services defined in `docker-compose.yml`:
- **djangoapp**: Main Django application (port 8000)
- **celery**: Background task worker
- **celery_beat**: Periodic task scheduler
- **psql**: PostgreSQL 13 database
- **redis**: Message broker for Celery
- **adminer**: Database management UI (port 8080)

All services share environment variables from `dotenv_files/.env`

### Form Patterns
Forms in this codebase follow a specific pattern for multi-tenant scoping:
- Forms accept `empresa` parameter in `__init__`
- Related field querysets are filtered by empresa: `self.fields['filial'].queryset = Filial.objects.filter(empresa=empresa)`
- This ensures users only see data from their company

### Important Field Behaviors
- Text fields (nome, documento, descricao) are auto-uppercased on save
- CNPJ fields strip non-numeric characters automatically
- ContaPagar uses Decimal for all monetary fields to avoid floating-point issues
- valor_saldo is calculated automatically: bruto + juros + multa + acrescimos - desconto - pago

## Configuration

### Environment Variables
Required in `dotenv_files/.env`:
- **Database**: DB_ENGINE, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
- **Django**: SECRET_KEY, DEBUG, ALLOWED_HOSTS
- **Celery**: CELERY_BROKER_URL (defaults to redis://localhost:6379/0)
- **Telegram**: TELEGRAM_TOKEN (for notifications)

### Static & Media Files
- Static files collected to `/data/web/static/`
- Media uploads to `/data/web/media/`
- Docker volumes persist data in `./data/`

## Code Conventions

### Naming
- Models use Portuguese business terminology (ContaPagar, Fornecedor, Filial)
- Status choices use snake_case ('a_vencer', 'vencida', 'pago', 'cancelado')
- All user-facing text is in Brazilian Portuguese

### Access Control
Always use `@grupos_necessarios("Administrador", "Financeiro")` decorator on financial views to enforce role-based access.

### Database Queries
Always filter by empresa when querying tenant-specific data:
```python
ContaPagar.objects.filter(empresa=request.user.empresa)
```

## OFX Reconciliation Workflow
1. User uploads OFX file via ConciliacaoForm
2. `processar_ofx()` in financeiro/utils.py parses transactions
3. System matches OFX entries against ContaPagar with status='pago' by:
   - Same valor (within 0.01 tolerance)
   - Same data_pagamento
   - Same filial
4. Unmatched items from both sides are displayed for manual review
5. User can create ContaPagar directly from unmatched OFX transactions

## Release Process
The project uses `release.py` for version management. Changelog entries are in Brazilian Portuguese with sections: Adicionado, Alterado, Corrigido.
