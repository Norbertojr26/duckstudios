"""Aplica o schema e as cargas. Roda a cada boot: os seeds são idempotentes, e o schema
só é criado se ainda não existir. Assim um deploy novo sobe com o parque inteiro dentro."""
import os
import sys
from pathlib import Path
import psycopg
from . import db

RAIZ = Path(__file__).resolve().parent.parent
SEEDS = ["db/seed_inventario.sql", "db/seed_02_regras.sql",
         "db/seed_03_catalogo.sql", "db/seed_04_precos_servico.sql",
         "db/seed_05_edicoes.sql"]          # o último só existe se você exportou/editou

# Mudanças de schema pós-lançamento. O schema.sql cria o banco do zero; um banco que já
# existe precisa destes ALTERs. Todos idempotentes — rodar de novo é sempre seguro.
MIGRACOES = [
    "ALTER TABLE rental ADD COLUMN IF NOT EXISTS assinante_nome text",
    "ALTER TABLE rental ADD COLUMN IF NOT EXISTS assinante_documento text",
    "ALTER TABLE project ADD COLUMN IF NOT EXISTS estado_editorial text NOT NULL DEFAULT 'ingerido'",
    """DO $$ BEGIN
         ALTER TABLE project ADD CONSTRAINT project_estado_editorial_chk
           CHECK (estado_editorial IN ('ingerido','em_edicao','aprovado','entregue'));
       EXCEPTION WHEN duplicate_object THEN NULL; END $$""",
    """CREATE TABLE IF NOT EXISTS maquina (
         id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
         nome text UNIQUE NOT NULL,
         ultimo_heartbeat timestamptz,
         info jsonb NOT NULL DEFAULT '{}')""",
    """CREATE TABLE IF NOT EXISTS maquina_pasta (
         id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
         maquina_id uuid NOT NULL REFERENCES maquina(id) ON DELETE CASCADE,
         caminho text NOT NULL,
         permissao text NOT NULL DEFAULT 'leitura'
           CHECK (permissao IN ('leitura','leitura_escrita')),
         ativo boolean NOT NULL DEFAULT true,
         UNIQUE (maquina_id, caminho))""",
    """CREATE TABLE IF NOT EXISTS usuario (
         id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
         nome text NOT NULL,
         email text UNIQUE NOT NULL,
         papel text NOT NULL DEFAULT 'diretor' CHECK (papel IN ('dev','diretor')),
         senha_hash text,
         foto bytea,
         foto_tipo text,
         convite_token text UNIQUE,
         ativo boolean NOT NULL DEFAULT true,
         criado_em timestamptz NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS sessao (
         token text PRIMARY KEY,
         usuario_id uuid NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
         criado_em timestamptz NOT NULL DEFAULT now(),
         expira_em timestamptz NOT NULL)""",
]


def semear_dev(conn):
    """Primeiro usuário: o dono, papel dev, com a APP_SENHA de hoje — assim o login por
    formulário nasce funcionando e a senha pode ser trocada no perfil depois."""
    senha = os.environ.get("APP_SENHA", "")
    if not senha or conn.execute("SELECT 1 FROM usuario LIMIT 1").fetchone():
        return
    from . import auth
    email = os.environ.get("APP_DEV_EMAIL", "duckcineproducoes@gmail.com")
    conn.execute("INSERT INTO usuario (nome, email, papel, senha_hash) "
                 "VALUES (%s, %s, 'dev', %s)", ("Duck", email, auth.gerar_hash(senha)))
    print(f"[migrar] usuário dev criado: {email} (senha = a APP_SENHA atual)")


def rodar():
    if not db.TEM_URL:
        print("[migrar] nenhuma URL de banco válida chegou no container.", file=sys.stderr)
        print(f"[migrar] procurei em: {', '.join(db.CANDIDATAS)}", file=sys.stderr)
        print(f"[migrar] variáveis parecidas com banco presentes: "
              f"{db.variaveis_de_banco() or 'NENHUMA'}", file=sys.stderr)
        for linha in db.diagnostico_url():
            print(f"[migrar] {linha}", file=sys.stderr)
        nao = db.referencias_nao_resolvidas()
        if nao:
            print(f"[migrar] ATENÇÃO: {nao} ainda contêm '${{{{...}}}}' — você copiou o TEMPLATE "
                  "em vez do valor. No serviço Postgres use o botão Connect e copie a "
                  "connection string já resolvida.", file=sys.stderr)
        print("[migrar] uma referência do Railway que não resolve chega VAZIA. Se o nome acima "
              "aparece na lista mas o valor não vale, a referência está apontando para um "
              "serviço com outro nome — ou cole a connection string literal.", file=sys.stderr)
        return False

    print(f"[migrar] banco: {db.onde()} (via {db.ORIGEM})")
    ok, erro = db.esperar()
    if not ok:
        print(f"[migrar] banco não respondeu em {db.ESPERA_SEG}s: {erro}", file=sys.stderr)
        if "password authentication failed" in str(erro):
            print("[migrar] O host respondeu, então a URL está quase certa — o que não bate é a "
                  "SENHA. Causa mais comum: o valor colado ainda tem ${{POSTGRES_PASSWORD}} "
                  "literal, ou veio truncado. No serviço Postgres, use Connect e copie a "
                  "connection string resolvida.", file=sys.stderr)
        return False

    with psycopg.connect(db.DSN, autocommit=True) as conn:
        existe = conn.execute("SELECT to_regclass('public.asset') IS NOT NULL AS t").fetchone()[0]
        if not existe:
            print("[migrar] criando schema")
            conn.execute((RAIZ / "db/schema.sql").read_text(encoding="utf-8"))
        for ddl in MIGRACOES:
            conn.execute(ddl)
        for s in SEEDS:
            f = RAIZ / s
            if not f.exists():
                continue
            print(f"[migrar] {s}")
            conn.execute(f.read_text(encoding="utf-8"))
        semear_dev(conn)
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
