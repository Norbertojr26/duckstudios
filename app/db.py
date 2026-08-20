"""Conexão e consultas. Toda leitura da interface tem par em /api — a tela e o agente
leem exatamente a mesma coisa, então não existe dado que só o humano enxerga."""
import os
from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

# Railway injeta DATABASE_URL no serviço quando o Postgres está anexado.
# O Railway pode expor a conexão com nomes diferentes conforme como o banco foi ligado.
# Uma referência que não resolve chega como string VAZIA, não ausente — por isso o filtro.
CANDIDATAS = ("DATABASE_URL", "DATABASE_PRIVATE_URL", "POSTGRES_URL",
              "POSTGRESQL_URL", "PG_URL", "DATABASE_PUBLIC_URL")


# Marca de referência do Railway que não foi resolvida. Se isso chega dentro do valor,
# o que temos é o TEMPLATE, não a senha — e o Postgres responde "password authentication failed".
NAO_RESOLVIDA = "${{"


def _limpar(v):
    """Aceita o que a pessoa realmente cola. O painel do Railway oferece a URL crua, mas também
    um comando psql pronto — e colar o comando inteiro é o erro mais fácil de cometer."""
    v = (v or "").strip().strip(";").strip()
    if v[:5].lower() == "psql ":                      # 'psql "postgresql://..."'
        v = v[5:].strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1].strip()                            # aspas em volta
    return v


def _achar_url():
    for nome in CANDIDATAS:
        v = _limpar(os.environ.get(nome))
        if v.startswith(("postgres://", "postgresql://")) and NAO_RESOLVIDA not in v:
            return nome, v
    # Sem URL utilizável, tenta montar a partir das peças (PGHOST/PGUSER/...), que é a
    # outra forma comum de o Railway expor a conexão.
    peca = {k: (os.environ.get(k) or "").strip() for k in
            ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE")}
    if peca["PGHOST"] and peca["PGUSER"] and NAO_RESOLVIDA not in "".join(peca.values()):
        from urllib.parse import quote
        senha = f":{quote(peca['PGPASSWORD'], safe='')}" if peca["PGPASSWORD"] else ""
        banco = peca["PGDATABASE"] or "railway"
        usuario = quote(peca["PGUSER"], safe="")
        if peca["PGHOST"].startswith("/"):      # socket local: host vai como parâmetro
            extra = f"?host={quote(peca['PGHOST'], safe='')}"
            if peca["PGPORT"]:
                extra += f"&port={peca['PGPORT']}"
            return "PG* (peças)", f"postgresql://{usuario}{senha}@/{banco}{extra}"
        porta = f":{peca['PGPORT']}" if peca["PGPORT"] else ""
        return "PG* (peças)", f"postgresql://{usuario}{senha}@{peca['PGHOST']}{porta}/{banco}"
    return None, None


def diagnostico_url():
    """Descreve o que chegou em cada candidata SEM revelar a senha: só tamanho e o começo do
    valor, que é sempre o esquema (postgresql://) e nunca a credencial."""
    fora = []
    for nome in CANDIDATAS:
        bruto = os.environ.get(nome)
        if bruto is None:
            continue
        v = _limpar(bruto)
        if not v:
            causa = "VAZIA (referência do Railway que não resolveu)"
        elif NAO_RESOLVIDA in v:
            causa = "contém ${{...}} — é o template, não o valor"
        elif v.startswith(("postgres://", "postgresql://")):
            continue                                   # esta serve
        else:
            causa = f"não começa com postgresql:// — começa com {v[:10]!r}"
        fora.append(f"{nome}: {causa} (tamanho {len(bruto)})")
    return fora


def referencias_nao_resolvidas():
    """Variáveis cujo valor ainda contém ${{...}} — o Railway não substituiu."""
    return sorted(k for k in CANDIDATAS + ("PGPASSWORD", "PGHOST", "PGUSER", "PGDATABASE")
                  if NAO_RESOLVIDA in (os.environ.get(k) or ""))


def variaveis_de_banco():
    """Nomes (nunca valores) das variáveis parecidas com banco que chegaram no container.
    É o que responde 'o Railway injetou alguma coisa?' sem vazar senha em log."""
    return sorted(k for k in os.environ
                  if any(t in k.upper() for t in ("DATABASE", "POSTGRES", "PG")))


ORIGEM, _url = _achar_url()
TEM_URL = bool(_url)
DSN = _url or "postgresql:///duck"
if DSN.startswith("postgres://"):          # forma antiga que o psycopg3 não aceita
    DSN = DSN.replace("postgres://", "postgresql://", 1)


def onde():
    """Host e banco, sem a senha — para aparecer em log e no /healthz sem vazar credencial."""
    try:
        resto = DSN.split("://", 1)[1]
        if "@" in resto:
            resto = resto.split("@", 1)[1]
        host, _, caminho = resto.partition("/")
        return f"{host}/{caminho.split('?')[0] or '?'}"
    except Exception:                                        # noqa: BLE001
        return "desconhecido"


_pool = ConnectionPool(DSN, min_size=1, max_size=8, kwargs={"row_factory": dict_row}, open=False)


def abrir():
    # wait=False de propósito: se o Postgres ainda não estiver de pé, o servidor sobe assim mesmo
    # e o /healthz explica o que está errado. Morrer no boot só produz um container em loop.
    _pool.open(wait=False)


ESPERA_SEG = int(os.environ.get("DB_ESPERA_SEG", "90"))


def esperar(segundos=None):
    """Aguarda o banco aceitar conexão. A rede privada da Railway leva alguns segundos para
    ficar pronta depois que o container inicia — tentar uma vez só falha por milésimos."""
    import time
    import psycopg
    segundos = ESPERA_SEG if segundos is None else segundos
    limite, espera, ultimo = time.time() + segundos, 1.0, None
    while time.time() < limite:
        try:
            with psycopg.connect(DSN, connect_timeout=5) as c:
                c.execute("SELECT 1")
            return True, None
        except Exception as e:                               # noqa: BLE001
            ultimo = e
            time.sleep(espera)
            espera = min(espera * 1.6, 8)
    return False, ultimo


@contextmanager
def cur():
    with _pool.connection() as conn, conn.cursor() as c:
        yield c


def q(sql, params=None):
    with cur() as c:
        c.execute(sql, params or ())
        return c.fetchall()


def q1(sql, params=None):
    r = q(sql, params)
    return r[0] if r else None


def exec_(sql, params=None):
    with cur() as c:
        c.execute(sql, params or ())
        return c.rowcount


# ---------------------------------------------------------------- consultas

RESUMO = """
SELECT
  (SELECT count(*) FROM rental_line WHERE status = 'em_campo')                       AS em_campo,
  (SELECT coalesce(sum(a.valor_reposicao), 0) FROM rental_line rl
     JOIN asset a ON a.id = rl.asset_id WHERE rl.status = 'em_campo')                AS valor_em_campo,
  (SELECT count(*) FROM rental r WHERE r.status = 'em_campo'
     AND r.previsao_devolucao < now())                                               AS atrasadas,
  (SELECT count(*) FROM asset WHERE proprietario = 'proprio' AND status = 'disponivel') AS disponiveis,
  (SELECT count(*) FROM asset WHERE proprietario = 'proprio')                        AS total_proprios,
  (SELECT coalesce(sum(valor_aquisicao), 0) FROM asset WHERE proprietario = 'proprio') AS patrimonio,
  (SELECT count(*) FROM asset WHERE proprietario = 'proprio'
     AND NOT valor_reposicao_confirmado)                                             AS a_confirmar,
  (SELECT count(*) FROM asset WHERE proprietario = 'proprio' AND numero_serie IS NULL) AS sem_serie
"""

EM_CAMPO = """
SELECT r.id, r.numero, r.tipo, r.checkout_at, r.previsao_devolucao,
       coalesce(r.responsavel_nome, c.nome, co.nome, 'Sem responsável') AS responsavel,
       (r.previsao_devolucao IS NOT NULL AND r.previsao_devolucao < now()) AS atrasado,
       count(rl.*) AS itens,
       string_agg(a.nome, ' · ' ORDER BY a.valor_aquisicao DESC NULLS LAST) AS lista
  FROM rental r
  JOIN rental_line rl ON rl.rental_id = r.id AND rl.status = 'em_campo'
  JOIN asset a        ON a.id = rl.asset_id
  LEFT JOIN contact c ON c.id = r.contact_id
  LEFT JOIN company co ON co.id = r.company_id
 WHERE r.status = 'em_campo'
 GROUP BY r.id, c.nome, co.nome
 ORDER BY atrasado DESC, r.checkout_at
"""
