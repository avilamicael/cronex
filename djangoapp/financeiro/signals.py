# financeiro/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from financeiro.models import CertificadoDigital, ConfiguracaoNFe


@receiver(post_save, sender=CertificadoDigital)
def criar_configuracao_nfe(sender, instance, created, **kwargs):
    """
    Cria automaticamente uma ConfiguracaoNFe quando um CertificadoDigital é criado.
    """
    if created:
        ConfiguracaoNFe.objects.get_or_create(certificado=instance)
        print(f"[Signal] ConfiguracaoNFe criada automaticamente para {instance.filial.nome}")
