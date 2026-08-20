"""Duck Studios — CRM de patrimônio e locação.

Toda tela tem par em /api. A interface e os agentes leem a mesma base pelas mesmas consultas:
não existe número na tela que um agente não consiga buscar.
"""
import base64, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db

RAIZ = Path(__file__).resolve().parent
app = FastAPI(title="Duck Studios", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")
tpl = Jinja2Templates(directory=str(RAIZ / "templates"))


def brl(v):
    if v is None:
        return "—"
    return f"R$ {float(v):,.2f}".replace(",", "~").replace(".", ",").replace("~", ".")


def curto(v):
    if v is None:
        return "—"
    v = float(v)
    return f"{v/1_000_000:.1f}M".replace(".", ",") if v >= 1_000_000 else f"{v/1000:.0f}k"


tpl.env.filters["brl"] = brl
tpl.env.filters["curto"] = curto


# ------------------------------------------------------------------ acesso
# O sistema inteiro (patrimônio, valores, clientes) atrás de uma URL pública sem senha seria
# um vazamento de meio milhão em equipamento. Basic auth é o mínimo — simples, funciona em
# qualquer navegador e não depende de mais nenhuma peça.
USUARIO = os.environ.get("APP_USUARIO", "duck")
SENHA = os.environ.get("APP_SENHA", "")
LIVRE = ("/healthz", "/static")


@app.middleware("http")
async def exigir_senha(request: Request, call_next):
    if SENHA and not request.url.path.startswith(LIVRE):
        cab = request.headers.get("authorization", "")
        ok = False
        if cab.startswith("Basic "):
            try:
                u, _, p = base64.b64decode(cab[6:]).decode().partition(":")
                ok = secrets.compare_digest(u, USUARIO) and secrets.compare_digest(p, SENHA)
            except Exception:                                # noqa: BLE001
                ok = False
        if not ok:
            return Response(status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Duck Studios"'})
    return await call_next(request)


@app.on_event("startup")
def _startup():
    db.abrir()
    if db.TEM_URL:
        print(f"[app] banco: {db.onde()} (via {db.ORIGEM})")
    else:
        print(f"[app] SEM banco. Variáveis parecidas com banco no container: "
              f"{db.variaveis_de_banco() or 'NENHUMA'}")
    if not SENHA:
        print("[ATENÇÃO] APP_SENHA não definida — a aplicação está aberta a quem tiver a URL.")


@app.get("/healthz")
def healthz():
    """Diz o que está errado, não só que está errado. Sem senha e sem credencial no corpo."""
    if not db.TEM_URL:
        return JSONResponse({"ok": False, "banco": None,
                             "erro": "nenhuma URL de banco válida no ambiente",
                             "procurei_em": list(db.CANDIDATAS),
                             "variaveis_presentes": db.variaveis_de_banco(),
                             "referencias_nao_resolvidas": db.referencias_nao_resolvidas(),
                             "por_que_recusei": db.diagnostico_url(),
                             "dica": "referência do Railway que não resolve chega vazia — "
                                     "confira o nome do serviço de banco"},
                            status_code=503)
    try:
        n = db.q1("SELECT count(*) AS n FROM asset")
        return {"ok": True, "banco": db.onde(), "via": db.ORIGEM, "itens": n["n"]}
    except Exception as e:                                  # noqa: BLE001
        return JSONResponse({"ok": False, "banco": db.onde(),
                             "erro": f"{type(e).__name__}: {e}"}, status_code=503)


def pag(request, nome, **ctx):
    # Starlette moderno espera (request, nome, contexto) — a ordem antiga silenciosamente
    # trata o dicionário como nome do template.
    return tpl.TemplateResponse(request, nome, {**ctx, "sem_senha": not SENHA})


# ------------------------------------------------------------------ painel

@app.get("/", response_class=HTMLResponse)
def painel(request: Request):
    return pag(request, "painel.html",
               ativo="painel", r=db.q1(db.RESUMO), saidas=db.q(db.EM_CAMPO),
               pendentes=db.q("""SELECT titulo, descricao FROM approval_request
                                  WHERE status = 'pendente' ORDER BY criado_em DESC LIMIT 5"""))


# ------------------------------------------------------------ equipamento

@app.get("/equipamento", response_class=HTMLResponse)
def equipamento(request: Request, busca: str = "", cat: str = "", dono: str = "proprio"):
    where, args = ["a.proprietario = %s"], [dono]
    if busca:
        where.append("(a.nome ILIKE %s OR a.codigo ILIKE %s OR a.marca ILIKE %s)")
        args += [f"%{busca}%"] * 3
    if cat:
        where.append("a.categoria = %s"); args.append(cat)
    itens = db.q(f"""
        SELECT a.*, rl.status AS situacao,
               coalesce(r.responsavel_nome, c.nome, co.nome) AS com_quem
          FROM asset a
          LEFT JOIN rental_line rl ON rl.asset_id = a.id AND rl.status = 'em_campo'
          LEFT JOIN rental r  ON r.id = rl.rental_id
          LEFT JOIN contact c ON c.id = r.contact_id
          LEFT JOIN company co ON co.id = r.company_id
         WHERE {' AND '.join(where)}
         ORDER BY a.codigo LIMIT 400""", args)
    cats = db.q("""SELECT categoria, count(*) n FROM asset WHERE proprietario = %s
                    GROUP BY 1 ORDER BY 1""", (dono,))
    return pag(request, "equipamento.html", ativo="equipamento", itens=itens, cats=cats,
               busca=busca, cat=cat, dono=dono)


@app.get("/equipamento/{codigo}", response_class=HTMLResponse)
def item(request: Request, codigo: str):
    a = db.q1("SELECT * FROM asset WHERE codigo = %s", (codigo,))
    if not a:
        return HTMLResponse("Item não encontrado", status_code=404)
    hist = db.q("""SELECT r.numero, r.tipo, r.checkout_at, r.checkin_at,
                          coalesce(r.responsavel_nome, c.nome, co.nome) AS responsavel
                     FROM rental_line rl JOIN rental r ON r.id = rl.rental_id
                     LEFT JOIN contact c ON c.id = r.contact_id
                     LEFT JOIN company co ON co.id = r.company_id
                    WHERE rl.asset_id = %s ORDER BY r.criado_em DESC LIMIT 20""", (a["id"],))
    dentro = db.q("SELECT codigo, nome FROM asset WHERE container_id = %s ORDER BY codigo",
                  (a["id"],))
    return pag(request, "item.html", ativo="equipamento", a=a, hist=hist, dentro=dentro)


# ----------------------------------------------------------------- saídas

@app.get("/saidas", response_class=HTMLResponse)
def saidas(request: Request):
    linhas = db.q("""
        SELECT r.*, coalesce(r.responsavel_nome, c.nome, co.nome) AS responsavel,
               count(rl.*) itens,
               count(*) FILTER (WHERE rl.status = 'devolvido') devolvidos,
               (r.previsao_devolucao IS NOT NULL AND r.previsao_devolucao < now()
                AND r.status = 'em_campo') AS atrasado
          FROM rental r
          LEFT JOIN rental_line rl ON rl.rental_id = r.id
          LEFT JOIN contact c ON c.id = r.contact_id
          LEFT JOIN company co ON co.id = r.company_id
         GROUP BY r.id, c.nome, co.nome ORDER BY r.criado_em DESC LIMIT 100""")
    return pag(request, "saidas.html", ativo="saidas", linhas=linhas)


@app.post("/saidas/nova")
def nova_saida(responsavel: str = Form(...), tipo: str = Form("emprestimo"),
               dias: int = Form(3)):
    agora = datetime.now(timezone.utc)
    fim = agora + timedelta(days=max(dias, 1))
    r = db.q1("""INSERT INTO rental (numero, tipo, responsavel_nome, status, inicio, fim,
                                     previsao_devolucao, checkout_at)
                 VALUES (to_char(now(),'YYMM')||'-'||lpad((
                           SELECT count(*)+1 FROM rental)::text, 3, '0'),
                         %s, %s, 'em_campo', %s, %s, %s, now())
                 RETURNING id""", (tipo, responsavel.strip(), agora, fim, fim))
    return RedirectResponse(f"/saidas/{r['id']}", status_code=303)


@app.get("/saidas/{rid}", response_class=HTMLResponse)
def saida(request: Request, rid: str, erro: str = "", ok: str = ""):
    r = db.q1("""SELECT r.*, coalesce(r.responsavel_nome, c.nome, co.nome) AS responsavel
                   FROM rental r LEFT JOIN contact c ON c.id = r.contact_id
                   LEFT JOIN company co ON co.id = r.company_id WHERE r.id = %s""", (rid,))
    if not r:
        return HTMLResponse("Saída não encontrada", status_code=404)
    itens = db.q("""SELECT rl.id, rl.status, a.codigo, a.nome, a.categoria,
                           a.valor_diaria, a.valor_reposicao, a.valor_reposicao_confirmado,
                           (SELECT count(*) FROM conference_check cc
                             WHERE cc.rental_id = rl.rental_id AND cc.asset_id = rl.asset_id
                               AND cc.momento = 'retorno') AS conferido_volta
                      FROM rental_line rl JOIN asset a ON a.id = rl.asset_id
                     WHERE rl.rental_id = %s ORDER BY a.valor_aquisicao DESC NULLS LAST""", (rid,))
    return pag(request, "saida.html", ativo="saidas", r=r, itens=itens, erro=erro, ok=ok)


@app.post("/saidas/{rid}/bipar")
def bipar(rid: str, codigo: str = Form(...), momento: str = Form("saida")):
    codigo = codigo.strip().upper()
    a = db.q1("SELECT * FROM asset WHERE upper(codigo) = %s", (codigo,))
    if not a:
        return RedirectResponse(f"/saidas/{rid}?erro=Código+{codigo}+não+existe", 303)

    if momento == "saida":
        if a["proprietario"] == "sublocado":
            return RedirectResponse(
                f"/saidas/{rid}?erro={a['codigo']}+é+sublocado:+cote+com+o+fornecedor+antes", 303)
        ja = db.q1("SELECT id FROM rental_line WHERE rental_id=%s AND asset_id=%s", (rid, a["id"]))
        if not ja:
            r = db.q1("SELECT inicio, fim FROM rental WHERE id = %s", (rid,))
            try:
                db.exec_("""INSERT INTO rental_line (rental_id, asset_id, during, status, valor_diaria)
                            VALUES (%s, %s, tstzrange(%s, %s), 'em_campo', %s)""",
                         (rid, a["id"], r["inicio"], r["fim"], a["valor_diaria"]))
            except Exception:                                # constraint de exclusão do banco
                return RedirectResponse(
                    f"/saidas/{rid}?erro={a['codigo']}+já+está+reservado+nesse+período", 303)
            db.exec_("UPDATE asset SET status='em_campo' WHERE id=%s", (a["id"],))
    else:
        rl = db.q1("SELECT id FROM rental_line WHERE rental_id=%s AND asset_id=%s", (rid, a["id"]))
        if not rl:
            return RedirectResponse(f"/saidas/{rid}?erro={a['codigo']}+não+saiu+nesta+saída", 303)
        db.exec_("UPDATE rental_line SET status='devolvido' WHERE id=%s", (rl["id"],))
        db.exec_("UPDATE asset SET status='disponivel' WHERE id=%s", (a["id"],))

    db.exec_("""INSERT INTO conference_check (rental_id, asset_id, momento, estado, operador, client_uuid)
                VALUES (%s, %s, %s, 'ok', 'web', %s)
                ON CONFLICT (rental_id, asset_id, momento) DO NOTHING""",
             (rid, a["id"], momento, str(uuid.uuid4())))
    return RedirectResponse(f"/saidas/{rid}?ok={a['codigo']}+{'conferido' if momento=='retorno' else 'adicionado'}", 303)


@app.post("/saidas/{rid}/fechar")
def fechar(rid: str):
    faltando = db.q1("""SELECT count(*) n FROM rental_line
                         WHERE rental_id = %s AND status <> 'devolvido'""", (rid,))
    if faltando["n"]:
        return RedirectResponse(
            f"/saidas/{rid}?erro=Faltam+{faltando['n']}+item(ns)+para+conferir", 303)
    db.exec_("UPDATE rental SET status='devolvido', checkin_at=now() WHERE id=%s", (rid,))
    return RedirectResponse(f"/saidas/{rid}?ok=Saída+encerrada", 303)


# -------------------------------------------------------------------- API
# Mesma verdade da interface, em JSON. É por aqui que os agentes leem e escrevem.

@app.get("/api/resumo")
def api_resumo():
    return db.q1(db.RESUMO)


@app.get("/api/em-campo")
def api_em_campo():
    return db.q(db.EM_CAMPO)


@app.get("/api/equipamento")
def api_equipamento(busca: str = "", dono: str = ""):
    where, args = ["1=1"], []
    if dono:
        where.append("proprietario = %s"); args.append(dono)
    if busca:
        where.append("(nome ILIKE %s OR codigo ILIKE %s)"); args += [f"%{busca}%"] * 2
    return db.q(f"""SELECT codigo, nome, categoria, marca, proprietario, status,
                           valor_diaria, valor_semanal, valor_mensal,
                           valor_reposicao, valor_reposicao_confirmado, requer_cotacao,
                           numero_serie
                      FROM asset WHERE {' AND '.join(where)} ORDER BY codigo""", args)


@app.get("/api/disponibilidade")
def api_disponibilidade(codigo: str, inicio: str, fim: str):
    a = db.q1("SELECT id, nome, proprietario, requer_cotacao FROM asset WHERE codigo = %s", (codigo,))
    if not a:
        return JSONResponse({"erro": "código não existe"}, 404)
    livre = db.q1("SELECT asset_disponivel(%s, %s, %s) AS livre", (a["id"], inicio, fim))
    return {"codigo": codigo, "nome": a["nome"], "livre": livre["livre"],
            "requer_cotacao": a["requer_cotacao"],
            "aviso": "item sublocado — cotar com o fornecedor antes de fechar preço"
                     if a["requer_cotacao"] else None}


@app.get("/api/precos")
def api_precos():
    return db.q("SELECT codigo, descricao, unidade, valor, categoria FROM price_list WHERE ativo")
