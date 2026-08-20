"""Aplica o schema e as cargas. Roda a cada boot: os seeds são idempotentes, e o schema
só é criado se ainda não existir. Assim um deploy novo sobe com o parque inteiro dentro."""
import sys
from pathlib import Path
import psycopg
from . import db

RAIZ = Path(__file__).resolve().parent.parent
SEEDS = ["db/seed_inventario.sql", "db/seed_02_regras.sql",
         "db/seed_03_catalogo.sql", "db/seed_04_precos_servico.sql",
         "db/seed_05_edicoes.sql"]          # o último só existe se você exportou/editou


def rodar():
    if not db.TEM_URL:
        print("[migrar] DATABASE_URL não está definida. No Railway, adicione a variável do "
              "serviço apontando para o Postgres: DATABASE_URL = ${{Postgres.DATABASE_URL}} "
              "(troque 'Postgres' pelo nome real do serviço de banco).", file=sys.stderr)
        return False

    print(f"[migrar] banco: {db.onde()}")
    ok, erro = db.esperar()
    if not ok:
        print(f"[migrar] banco não respondeu em 90s: {erro}", file=sys.stderr)
        return False

    with psycopg.connect(db.DSN, autocommit=True) as conn:
        existe = conn.execute("SELECT to_regclass('public.asset') IS NOT NULL AS t").fetchone()[0]
        if not existe:
            print("[migrar] criando schema")
            conn.execute((RAIZ / "db/schema.sql").read_text(encoding="utf-8"))
        for s in SEEDS:
            f = RAIZ / s
            if not f.exists():
                continue
            print(f"[migrar] {s}")
            conn.execute(f.read_text(encoding="utf-8"))
        n = conn.execute("SELECT count(*) FROM asset").fetchone()[0]
        print(f"[migrar] pronto — {n} itens")
    return True


if __name__ == "__main__":
    # Nunca derruba o container: sem servidor não há log nem /healthz para diagnosticar.
    # O healthcheck da Railway continua reprovando enquanto o banco não estiver certo.
    try:
        rodar()
    except Exception as e:                                   # noqa: BLE001
        print(f"[migrar] FALHOU: {type(e).__name__}: {e}", file=sys.stderr)
