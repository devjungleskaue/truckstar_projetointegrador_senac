"""
Hash e verificação de senhas usando PBKDF2-HMAC-SHA256 + salt aleatório.
Só usa stdlib (hashlib, secrets, hmac).
"""
import hashlib
import secrets
import hmac
import config


_LEGACY_ITERACOES = 100_000


def gerar_salt() -> str:
    """Salt aleatório em hex (32 chars = 16 bytes)."""
    return secrets.token_hex(16)


def _pbkdf2(senha: str, salt: str, iteracoes: int) -> str:
    if not isinstance(senha, str) or not isinstance(salt, str):
        raise TypeError("senha e salt precisam ser strings")
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        senha.encode('utf-8'),
        salt.encode('utf-8'),
        iteracoes,
    )
    return dk.hex()


def hash_senha(senha: str, salt: str) -> str:
    """Gera hash com a iteração configurada atualmente."""
    return _pbkdf2(senha, salt, config.HASH_ITERACOES)


def verificar_senha(senha: str, salt: str, hash_armazenado: str) -> bool:
    """
    Comparação resistente a timing attacks.
    Tenta primeiro com a iteração atual; se falhar e existir uma legada
    diferente, tenta também — útil pra hashes antigos no banco após
    bumps de HASH_ITERACOES (não perde acesso de usuários existentes).
    """
    if not hash_armazenado:
        return False
    armazenado = hash_armazenado
    try:
        atual = _pbkdf2(senha, salt, config.HASH_ITERACOES)
    except Exception:
        return False
    if hmac.compare_digest(atual, armazenado):
        return True
    if config.HASH_ITERACOES != _LEGACY_ITERACOES:
        try:
            legado = _pbkdf2(senha, salt, _LEGACY_ITERACOES)
        except Exception:
            return False
        return hmac.compare_digest(legado, armazenado)
    return False
