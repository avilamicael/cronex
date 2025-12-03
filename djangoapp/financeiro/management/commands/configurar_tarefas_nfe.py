# financeiro/management/commands/configurar_tarefas_nfe.py
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json


class Command(BaseCommand):
    help = 'Configura as tarefas periódicas para importação automática de NFe'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔧 Configurando tarefas periódicas de NFe...\n'))

        # 1. Criar schedule de 4 horas
        schedule_4h, created = IntervalSchedule.objects.get_or_create(
            every=4,
            period=IntervalSchedule.HOURS,
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Schedule de 4 horas criado'))
        else:
            self.stdout.write('  • Schedule de 4 horas já existe')

        # 2. Criar schedule de 30 minutos (para busca histórica incremental)
        schedule_30min, created = IntervalSchedule.objects.get_or_create(
            every=30,
            period=IntervalSchedule.MINUTES,
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Schedule de 30 minutos criado'))
        else:
            self.stdout.write('  • Schedule de 30 minutos já existe')

        # 3. Criar task de busca automática (a cada 4 horas)
        task_auto, created = PeriodicTask.objects.get_or_create(
            name='Buscar NFe automaticamente',
            defaults={
                'task': 'Buscar notas fiscais automaticamente',
                'interval': schedule_4h,
                'enabled': True,
                'description': 'Busca novas notas fiscais na SEFAZ automaticamente para certificados ativos'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Task "Buscar NFe automaticamente" criada'))
        else:
            self.stdout.write('  • Task "Buscar NFe automaticamente" já existe')
            # Atualiza o schedule caso tenha mudado
            task_auto.interval = schedule_4h
            task_auto.save()

        # 4. Criar task de busca histórica (a cada 30 minutos)
        task_historico, created = PeriodicTask.objects.get_or_create(
            name='Buscar histórico de NFe',
            defaults={
                'task': 'Buscar histórico de notas fiscais',
                'interval': schedule_30min,
                'enabled': True,
                'description': 'Busca histórico completo de notas fiscais de forma incremental'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Task "Buscar histórico de NFe" criada'))
        else:
            self.stdout.write('  • Task "Buscar histórico de NFe" já existe')
            # Atualiza o schedule caso tenha mudado
            task_historico.interval = schedule_30min
            task_historico.save()

        self.stdout.write(self.style.SUCCESS('\n✅ Configuração concluída!\n'))
        self.stdout.write('📋 Resumo:')
        self.stdout.write(f'   • Busca automática: A cada 4 horas')
        self.stdout.write(f'   • Busca histórica: A cada 30 minutos (apenas se ativada)\n')
        self.stdout.write(self.style.WARNING('⚠️  Para ativar a busca automática para um certificado:'))
        self.stdout.write('   1. Acesse o Django Admin')
        self.stdout.write('   2. Vá em Configurações NFe')
        self.stdout.write('   3. Crie/edite a configuração do certificado')
        self.stdout.write('   4. Marque "Busca Automática Ativa"\n')
