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


if __name__ == "__main__":
    try:
        rodar()
    except Exception as e:                                   # noqa: BLE001
        print(f"[migrar] FALHOU: {e}", file=sys.stderr)
        sys.exit(1)
