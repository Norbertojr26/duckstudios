"""Senhas e sessões — só biblioteca padrão, nada de dependência nova.

scrypt (stdlib) para hash de senha; sessão é uma linha no Postgres apontada por um cookie
opaco. Revogar acesso = apagar a linha — o banco continua sendo a única memória.
"""
import hashlib
import secrets

_PARAMS = dict(n=2 ** 14, r=8, p=1)


def gerar_hash(senha: str) -> str:
    sal = secrets.token_hex(16)
    h = hashlib.scrypt(senha.encode(), salt=bytes.fromhex(sal), **_PARAMS).hex()
    return f"scrypt${sal}${h}"


def conferir(senha: str, guardado: str | None) -> bool:
    try:
        _, sal, h = (guardado or "").split("$")
        calc = hashlib.scrypt(senha.encode(), salt=bytes.fromhex(sal), **_PARAMS).hex()
        return secrets.compare_digest(calc, h)
    except (ValueError, AttributeError):
        return False


def novo_token() -> str:
    return secrets.token_urlsafe(32)
