# Generated by Django 4.2.20 on 2025-05-07 18:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_user_empresa'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='telefone',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='telegram_chat_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
