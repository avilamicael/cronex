# Generated by Django 4.2.20 on 2025-05-06 02:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '0005_alter_contapagar_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contapagar',
            name='status',
            field=models.CharField(choices=[('a_vencer', 'À Vencer'), ('pago', 'Pago'), ('vencida', 'Vencida'), ('cancelado', 'Cancelado')], default='a_vencer', max_length=20),
        ),
    ]
