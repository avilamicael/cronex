"""
Utilitário para criptografia de senhas dos certificados digitais.
Usa Fernet (criptografia simétrica) com chave derivada do SECRET_KEY do Django.
"""
from cryptography.fernet import Fernet
from django.conf import settings
import hashlib
import base64


def _get_cipher():
    """
    Cria cipher Fernet usando SECRET_KEY do Django.
    A chave precisa ter exatamente 32 bytes URL-safe base64-encoded.
    """
    # Deriva uma chave de 32 bytes do SECRET_KEY
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    # Converte para base64 URL-safe (formato exigido pelo Fernet)
    key_b64 = base64.urlsafe_b64encode(key)
    return Fernet(key_b64)


def encrypt_password(password: str) -> bytes:
    """
    Criptografa uma senha de certificado.

    Args:
        password: Senha em texto plano

    Returns:
        bytes: Senha criptografada
    """
    if not password:
        raise ValueError("Senha não pode ser vazia")

    cipher = _get_cipher()
    return cipher.encrypt(password.encode('utf-8'))


def decrypt_password(encrypted_password) -> str:
    """
    Descriptografa uma senha de certificado.

    Args:
        encrypted_password: Senha criptografada (bytes, memoryview, etc)

    Returns:
        str: Senha em texto plano
    """
    if not encrypted_password:
        raise ValueError("Senha criptografada não pode ser vazia")

    # Converte memoryview para bytes (compatibilidade com BinaryField do Django)
    if isinstance(encrypted_password, memoryview):
        encrypted_password = bytes(encrypted_password)

    cipher = _get_cipher()
    return cipher.decrypt(encrypted_password).decode('utf-8')


def test_encryption():
    """
    Testa a criptografia/descriptografia.
    Use apenas para debugging.
    """
    test_password = "Teste123!"
    encrypted = encrypt_password(test_password)
    decrypted = decrypt_password(encrypted)

    print(f"Original:      {test_password}")
    print(f"Encrypted:     {encrypted}")
    print(f"Decrypted:     {decrypted}")
    print(f"Match:         {test_password == decrypted}")

    return test_password == decrypted
