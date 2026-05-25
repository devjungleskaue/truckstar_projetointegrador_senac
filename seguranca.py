"""
Hash e verificação de senhas usando PBKDF2-HMAC-SHA256 + salt aleatório.
Só usa stdlib (hashlib, secrets).
"""
import hashlib
import secrets
import hmac
import config


def gerar_salt() -> str:
    """Salt aleatório em hex (32 chars = 16 bytes)."""
    return secrets.token_hex(16)


def hash_senha(senha: str, salt: str) -> str:
    """PBKDF2-HMAC-SHA256, retorna hex."""
    if not isinstance(senha, str) or not isinstance(salt, str):
        raise TypeError("senha e salt precisam ser strings")
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        senha.encode('utf-8'),
        salt.encode('utf-8'),
        config.HASH_ITERACOES,
    )
    return dk.hex()


def verificar_senha(senha: str, salt: str, hash_armazenado: str) -> bool:
    """Comparação resistente a timing attacks."""
    try:
        calculado = hash_senha(senha, salt)
    except Exception:
        return False
    return hmac.compare_digest(calculado, hash_armazenado or '')
