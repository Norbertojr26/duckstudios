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
from .agentes import agenda as agentes_agenda

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


def qtd(v):
    if v is None:
        return "—"
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:.1f}".replace(".", ",")


tpl.env.filters["brl"] = brl
tpl.env.filters["curto"] = curto
tpl.env.filters["qtd"] = qtd


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
    agentes_agenda.iniciar()


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


def _bipar(rid: str, codigo: str, momento: str, client_uuid: str | None = None):
    """Regra única de conferência. HTML e API entram por aqui — se divergissem, a tela e o
    agente passariam a discordar sobre o que aconteceu."""
    codigo = (codigo or "").strip().upper()
    a = db.q1("SELECT * FROM asset WHERE upper(codigo) = %s", (codigo,))
    if not a:
        return False, f"Código {codigo} não existe", None

    if momento == "saida":
        if a["proprietario"] == "sublocado":
            return False, f"{a['codigo']} é sublocado: cote com o fornecedor antes", None
        ja = db.q1("SELECT id FROM rental_line WHERE rental_id=%s AND asset_id=%s", (rid, a["id"]))
        if not ja:
            r = db.q1("SELECT inicio, fim FROM rental WHERE id = %s", (rid,))
            if not r:
                return False, "Saída não encontrada", None
            try:
                db.exec_("""INSERT INTO rental_line (rental_id, asset_id, during, status, valor_diaria)
                            VALUES (%s, %s, tstzrange(%s, %s), 'em_campo', %s)""",
                         (rid, a["id"], r["inicio"], r["fim"], a["valor_diaria"]))
            except Exception:                            # constraint de exclusão do banco
                return False, f"{a['codigo']} já está reservado nesse período", None
            db.exec_("UPDATE asset SET status='em_campo' WHERE id=%s", (a["id"],))
    else:
        rl = db.q1("SELECT id FROM rental_line WHERE rental_id=%s AND asset_id=%s", (rid, a["id"]))
        if not rl:
            return False, f"{a['codigo']} não saiu nesta saída", None
        db.exec_("UPDATE rental_line SET status='devolvido' WHERE id=%s", (rl["id"],))
        db.exec_("UPDATE asset SET status='disponivel' WHERE id=%s", (a["id"],))

    # client_uuid vem do celular: a mesma bipada reenviada depois de operar offline
    # não vira duas conferências.
    db.exec_("""INSERT INTO conference_check (rental_id, asset_id, momento, estado, operador, client_uuid)
                VALUES (%s, %s, %s, 'ok', 'web', %s)
                ON CONFLICT (client_uuid) DO NOTHING""",
             (rid, a["id"], momento, client_uuid or str(uuid.uuid4())))
    return True, f"{a['codigo']} {'conferido' if momento == 'retorno' else 'adicionado'}", a


@app.post("/saidas/{rid}/bipar")
def bipar(rid: str, codigo: str = Form(...), momento: str = Form("saida")):
    ok, msg, _ = _bipar(rid, codigo, momento)
    chave = "ok" if ok else "erro"
    return RedirectResponse(f"/saidas/{rid}?{chave}={msg.replace(' ', '+')}", 303)


@app.post("/api/saidas/{rid}/bipar")
def api_bipar(rid: str, dados: dict):
    """Usado pelo scanner. Idempotente por client_uuid — reenviar não duplica."""
    ok, msg, a = _bipar(rid, dados.get("codigo", ""), dados.get("momento", "saida"),
                        dados.get("client_uuid"))
    return JSONResponse({"ok": ok, "mensagem": msg,
                         "item": {"codigo": a["codigo"], "nome": a["nome"],
                                  "categoria": a["categoria"],
                                  "valor_diaria": float(a["valor_diaria"] or 0)} if a else None},
                        status_code=200 if ok else 409)


@app.post("/saidas/{rid}/fechar")
def fechar(rid: str):
    faltando = db.q1("""SELECT count(*) n FROM rental_line
                         WHERE rental_id = %s AND status <> 'devolvido'""", (rid,))
    if faltando["n"]:
        return RedirectResponse(
            f"/saidas/{rid}?erro=Faltam+{faltando['n']}+item(ns)+para+conferir", 303)
    db.exec_("UPDATE rental SET status='devolvido', checkin_at=now() WHERE id=%s", (rid,))
    return RedirectResponse(f"/saidas/{rid}?ok=Saída+encerrada", 303)


# ------------------------------------------------------------------ termo

def _dados_termo(rid):
    r = db.q1("""SELECT r.*, coalesce(r.responsavel_nome, c.nome, co.nome) AS responsavel,
                        co.nome AS empresa, c.cpf, c.telefone_e164
                   FROM rental r LEFT JOIN contact c ON c.id = r.contact_id
                   LEFT JOIN company co ON co.id = r.company_id WHERE r.id = %s""", (rid,))
    if not r:
        return None, None
    itens = db.q("""SELECT a.codigo, a.nome, a.marca, a.numero_serie,
                           a.valor_reposicao, a.valor_reposicao_confirmado, a.valor_diaria
                      FROM rental_line rl JOIN asset a ON a.id = rl.asset_id
                     WHERE rl.rental_id = %s
                     ORDER BY a.valor_reposicao DESC NULLS LAST, a.codigo""", (rid,))
    return r, itens


@app.get("/saidas/{rid}/termo", response_class=HTMLResponse)
def termo(request: Request, rid: str):
    r, itens = _dados_termo(rid)
    if not r:
        return HTMLResponse("Saída não encontrada", status_code=404)
    total_reposicao = sum(float(i["valor_reposicao"] or 0) for i in itens)
    estimados = sum(1 for i in itens if not i["valor_reposicao_confirmado"])
    return tpl.TemplateResponse(request, "termo.html",
                                {"r": r, "itens": itens, "total_reposicao": total_reposicao,
                                 "estimados": estimados})


@app.post("/saidas/{rid}/assinar")
def assinar(rid: str, assinatura: str = Form(...), assinante_nome: str = Form(...),
            assinante_documento: str = Form("")):
    # A assinatura chega como data-URI PNG do canvas. Validar o prefixo evita gravar
    # qualquer outra coisa no lugar de uma imagem.
    if not assinatura.startswith("data:image/png;base64,") or len(assinatura) < 200:
        return RedirectResponse(f"/saidas/{rid}/termo?erro=assinatura+vazia", 303)
    if len(assinatura) > 400_000:
        return RedirectResponse(f"/saidas/{rid}/termo?erro=assinatura+grande+demais", 303)
    db.exec_("""UPDATE rental SET assinatura_path = %s, assinante_nome = %s,
                assinante_documento = NULLIF(%s, ''), termo_assinado_em = now()
                 WHERE id = %s AND termo_assinado_em IS NULL""",
             (assinatura, assinante_nome.strip(), assinante_documento.strip(), rid))
    db.exec_("""INSERT INTO activity (entidade_tipo, entidade_id, tipo, conteudo, autor)
                VALUES ('rental', %s, 'evento_sistema', %s, 'humano')""",
             (rid, f"termo assinado por {assinante_nome.strip()}"))
    return RedirectResponse(f"/saidas/{rid}/termo", 303)


# ------------------------------------------------------------ conferência

@app.get("/conferencia", response_class=HTMLResponse)
def conferencia(request: Request):
    abertas = db.q("""
        SELECT r.id, r.numero, r.tipo, r.checkout_at, r.previsao_devolucao,
               coalesce(r.responsavel_nome, c.nome, co.nome, 'Sem responsável') AS responsavel,
               count(rl.*) AS itens,
               count(*) FILTER (WHERE rl.status = 'devolvido') AS devolvidos,
               (r.previsao_devolucao IS NOT NULL AND r.previsao_devolucao < now()) AS atrasado,
               coalesce(sum(a.valor_reposicao), 0) AS exposicao
          FROM rental r
          JOIN rental_line rl ON rl.rental_id = r.id
          JOIN asset a        ON a.id = rl.asset_id
          LEFT JOIN contact c ON c.id = r.contact_id
          LEFT JOIN company co ON co.id = r.company_id
         WHERE r.status = 'em_campo'
         GROUP BY r.id, c.nome, co.nome
         ORDER BY atrasado DESC, r.previsao_devolucao NULLS LAST""")
    return pag(request, "conferencia.html", ativo="conferencia", abertas=abertas)


# ------------------------------------------------------------------ kits

@app.get("/kits", response_class=HTMLResponse)
def kits(request: Request):
    linhas = db.q("""
        SELECT k.id, k.nome, k.descricao, k.valor_diaria,
               count(ki.*) AS itens,
               sum(a.valor_aquisicao) AS patrimonio,
               sum(a.valor_diaria)    AS soma_diarias,
               count(*) FILTER (WHERE a.status <> 'disponivel') AS indisponiveis
          FROM kit k
          JOIN kit_item ki ON ki.kit_id = k.id
          JOIN asset a     ON a.id = ki.asset_id
         GROUP BY k.id ORDER BY sum(a.valor_aquisicao) DESC""")
    itens = db.q("""SELECT ki.kit_id, a.codigo, a.nome, a.status, a.valor_diaria
                      FROM kit_item ki JOIN asset a ON a.id = ki.asset_id
                     ORDER BY a.valor_aquisicao DESC NULLS LAST""")
    por_kit = {}
    for i in itens:
        por_kit.setdefault(i["kit_id"], []).append(i)
    return pag(request, "kits.html", ativo="kits", linhas=linhas, por_kit=por_kit)


# ---------------------------------------------------------------- preços

@app.get("/precos", response_class=HTMLResponse)
def precos(request: Request):
    servico = db.q("""SELECT categoria, codigo, descricao, unidade, valor
                        FROM price_list WHERE ativo ORDER BY categoria, codigo""")
    grupos = {}
    for l in servico:
        grupos.setdefault(l["categoria"] or "outros", []).append(l)
    locacao = db.q("""
        SELECT categoria, count(*) n,
               round(avg(100 * valor_diaria / NULLIF(valor_aquisicao, 0))::numeric, 2) pct,
               sum(valor_diaria) diaria, sum(valor_semanal) semanal, sum(valor_mensal) mensal
          FROM asset WHERE proprietario = 'proprio' AND valor_diaria IS NOT NULL
         GROUP BY categoria ORDER BY sum(valor_diaria) DESC""")
    return pag(request, "precos.html", ativo="precos", grupos=grupos, locacao=locacao)


# ------------------------------------------------------------ propostas

@app.get("/propostas", response_class=HTMLResponse)
def propostas(request: Request):
    linhas = db.q("""SELECT q.*, d.titulo, co.nome AS empresa, count(qi.*) itens
                       FROM quote q
                       LEFT JOIN deal d ON d.id = q.deal_id
                       LEFT JOIN company co ON co.id = d.company_id
                       LEFT JOIN quote_item qi ON qi.quote_id = q.id
                      GROUP BY q.id, d.titulo, co.nome ORDER BY q.criado_em DESC""")
    return pag(request, "propostas.html", ativo="propostas", linhas=linhas,
               negocios=db.q("""SELECT d.id, d.titulo, co.nome AS empresa FROM deal d
                                LEFT JOIN company co ON co.id = d.company_id
                                WHERE d.estagio NOT IN ('ganho','perdido')
                                ORDER BY d.criado_em DESC"""))


@app.post("/propostas/nova")
def proposta_nova(deal_id: str = Form(...), validade_dias: int = Form(15)):
    q = db.q1("""INSERT INTO quote (deal_id, numero, validade, criado_por)
                 VALUES (%s, to_char(now(),'YYMM')||'-'||lpad((SELECT count(*)+1 FROM quote)::text,3,'0'),
                         (now() + make_interval(days => %s))::date, 'humano')
                 RETURNING id""", (deal_id, validade_dias))
    return RedirectResponse(f"/propostas/{q['id']}", 303)


@app.get("/propostas/{qid}", response_class=HTMLResponse)
def proposta(request: Request, qid: str, erro: str = ""):
    q = db.q1("""SELECT q.*, d.titulo, d.data_evento, co.nome AS empresa, c.nome AS contato
                   FROM quote q LEFT JOIN deal d ON d.id = q.deal_id
                   LEFT JOIN company co ON co.id = d.company_id
                   LEFT JOIN contact c ON c.id = d.contact_id WHERE q.id = %s""", (qid,))
    if not q:
        return HTMLResponse("Proposta não encontrada", status_code=404)
    return pag(request, "proposta.html", ativo="propostas", q=q, erro=erro,
               itens=db.q("SELECT * FROM quote_item WHERE quote_id=%s ORDER BY descricao", (qid,)),
               precos=db.q("SELECT * FROM price_list WHERE ativo ORDER BY categoria, codigo"),
               kits=db.q("SELECT id, nome, valor_diaria FROM kit ORDER BY valor_diaria DESC"))


@app.post("/propostas/{qid}/item")
def proposta_item(qid: str, origem: str = Form(...), referencia: str = Form(""),
                  descricao: str = Form(""), quantidade: float = Form(1),
                  valor_unitario: str = Form("")):
    if origem == "tabela" and referencia:
        p = db.q1("SELECT * FROM price_list WHERE id = %s", (referencia,))
        if not p:
            return RedirectResponse(f"/propostas/{qid}?erro=Item+de+tabela+não+encontrado", 303)
        db.exec_("""INSERT INTO quote_item (quote_id, price_list_id, descricao, quantidade, valor_unitario)
                    VALUES (%s, %s, %s, %s, %s)""",
                 (qid, p["id"], p["descricao"], quantidade, p["valor"]))
    elif origem == "equipamento" and referencia:
        a = db.q1("SELECT * FROM asset WHERE upper(codigo) = upper(%s)", (referencia.strip(),))
        if not a:
            return RedirectResponse(f"/propostas/{qid}?erro=Código+não+encontrado", 303)
        if a["requer_cotacao"]:
            return RedirectResponse(
                f"/propostas/{qid}?erro={a['codigo']}+é+sublocado:+cote+antes+de+incluir", 303)
        db.exec_("""INSERT INTO quote_item (quote_id, descricao, quantidade, valor_unitario)
                    VALUES (%s, %s, %s, %s)""",
                 (qid, f"Locação — {a['nome']} ({a['codigo']})", quantidade, a["valor_diaria"]))
    elif origem == "kit" and referencia:
        k = db.q1("SELECT * FROM kit WHERE id = %s", (referencia,))
        db.exec_("""INSERT INTO quote_item (quote_id, descricao, quantidade, valor_unitario)
                    VALUES (%s, %s, %s, %s)""",
                 (qid, f"Locação — kit {k['nome']}", quantidade, k["valor_diaria"]))
    else:
        # Item fora de tabela fica com price_list_id nulo de propósito: é o sinal de que
        # alguém inventou um preço, e é isso que a revisão precisa ver.
        db.exec_("""INSERT INTO quote_item (quote_id, descricao, quantidade, valor_unitario)
                    VALUES (%s, %s, %s, NULLIF(%s,'')::numeric)""",
                 (qid, descricao.strip() or "Item avulso", quantidade, valor_unitario))
    _recalcular(qid)
    return RedirectResponse(f"/propostas/{qid}", 303)


@app.post("/propostas/{qid}/remover/{iid}")
def proposta_remover(qid: str, iid: str):
    db.exec_("DELETE FROM quote_item WHERE id=%s AND quote_id=%s", (iid, qid))
    _recalcular(qid)
    return RedirectResponse(f"/propostas/{qid}", 303)


@app.post("/propostas/{qid}/desconto")
def proposta_desconto(qid: str, desconto: str = Form("0")):
    db.exec_("UPDATE quote SET desconto = coalesce(NULLIF(%s,'')::numeric, 0) WHERE id=%s",
             (desconto, qid))
    _recalcular(qid)
    return RedirectResponse(f"/propostas/{qid}", 303)


def _recalcular(qid):
    db.exec_("""UPDATE quote SET subtotal = s.t,
                                 total = greatest(s.t - coalesce(desconto, 0), 0)
                  FROM (SELECT coalesce(sum(total), 0) t FROM quote_item WHERE quote_id=%s) s
                 WHERE quote.id = %s""", (qid, qid))


@app.get("/propostas/{qid}/imprimir", response_class=HTMLResponse)
def proposta_imprimir(request: Request, qid: str):
    q = db.q1("""SELECT q.*, d.titulo, d.data_evento, co.nome AS empresa, c.nome AS contato
                   FROM quote q LEFT JOIN deal d ON d.id = q.deal_id
                   LEFT JOIN company co ON co.id = d.company_id
                   LEFT JOIN contact c ON c.id = d.contact_id WHERE q.id = %s""", (qid,))
    itens = db.q("SELECT * FROM quote_item WHERE quote_id=%s ORDER BY descricao", (qid,))
    return tpl.TemplateResponse(request, "proposta_imprimir.html", {"q": q, "itens": itens})


# ------------------------------------------------------------- clientes

@app.get("/clientes", response_class=HTMLResponse)
def clientes(request: Request, busca: str = ""):
    onde, args = "", []
    if busca:
        onde = "WHERE co.nome ILIKE %s OR c.nome ILIKE %s OR c.email ILIKE %s"
        args = [f"%{busca}%"] * 3
    linhas = db.q(f"""
        SELECT co.id, co.nome, co.tipo, co.cnpj, co.criado_em,
               count(DISTINCT d.id) AS negocios,
               count(DISTINCT r.id) AS locacoes,
               coalesce(sum(DISTINCT p.valor_contrato), 0) AS contratado
          FROM company co
          LEFT JOIN contact c ON c.company_id = co.id
          LEFT JOIN deal d    ON d.company_id = co.id
          LEFT JOIN rental r  ON r.company_id = co.id
          LEFT JOIN project p ON p.company_id = co.id
          {onde}
         GROUP BY co.id ORDER BY co.nome""", args)
    soltos = db.q("""SELECT id, nome, email, telefone_e164, origem FROM contact
                      WHERE company_id IS NULL ORDER BY criado_em DESC LIMIT 50""")
    return pag(request, "clientes.html", ativo="clientes", linhas=linhas, soltos=soltos, busca=busca)


@app.post("/clientes/novo")
def cliente_novo(nome: str = Form(...), tipo: str = Form("cliente"),
                 contato: str = Form(""), email: str = Form(""), telefone: str = Form("")):
    co = db.q1("INSERT INTO company (nome, tipo) VALUES (%s, %s) RETURNING id",
               (nome.strip(), tipo))
    if contato.strip():
        db.exec_("""INSERT INTO contact (company_id, nome, email, telefone_e164, origem)
                    VALUES (%s, %s, NULLIF(%s,''), NULLIF(%s,''), 'manual')
                    ON CONFLICT DO NOTHING""",
                 (co["id"], contato.strip(), email.strip(), telefone.strip()))
    return RedirectResponse(f"/clientes/{co['id']}", 303)


@app.get("/clientes/{cid}", response_class=HTMLResponse)
def cliente(request: Request, cid: str):
    co = db.q1("SELECT * FROM company WHERE id = %s", (cid,))
    if not co:
        return HTMLResponse("Cliente não encontrado", status_code=404)
    return pag(request, "cliente.html", ativo="clientes", co=co,
               contatos=db.q("SELECT * FROM contact WHERE company_id = %s ORDER BY nome", (cid,)),
               negocios=db.q("""SELECT * FROM deal WHERE company_id = %s
                                 ORDER BY criado_em DESC""", (cid,)),
               locacoes=db.q("""SELECT r.*, count(rl.*) itens FROM rental r
                                LEFT JOIN rental_line rl ON rl.rental_id = r.id
                                WHERE r.company_id = %s GROUP BY r.id
                                ORDER BY r.criado_em DESC LIMIT 20""", (cid,)),
               atividades=db.q("""SELECT * FROM activity WHERE entidade_tipo='company'
                                   AND entidade_id=%s ORDER BY criado_em DESC LIMIT 40""", (cid,)))


@app.post("/clientes/{cid}/nota")
def cliente_nota(cid: str, texto: str = Form(...)):
    db.exec_("""INSERT INTO activity (entidade_tipo, entidade_id, tipo, conteudo, autor)
                VALUES ('company', %s, 'nota', %s, 'humano')""", (cid, texto.strip()))
    return RedirectResponse(f"/clientes/{cid}", 303)


# ----------------------------------------------------------------- funil

ESTAGIOS = ["novo", "qualificado", "proposta_enviada", "negociacao", "ganho", "perdido"]


@app.get("/funil", response_class=HTMLResponse)
def funil(request: Request):
    linhas = db.q("""
        SELECT d.*, co.nome AS empresa, c.nome AS contato,
               (SELECT max(criado_em) FROM activity a
                 WHERE a.entidade_tipo='deal' AND a.entidade_id = d.id) AS ultimo_toque
          FROM deal d
          LEFT JOIN company co ON co.id = d.company_id
          LEFT JOIN contact c  ON c.id = d.contact_id
         ORDER BY d.atualizado_em DESC""")
    colunas = {e: [] for e in ESTAGIOS}
    for l in linhas:
        colunas.setdefault(l["estagio"], []).append(l)
    return pag(request, "funil.html", ativo="funil", colunas=colunas, estagios=ESTAGIOS,
               empresas=db.q("SELECT id, nome FROM company ORDER BY nome"))


@app.post("/funil/novo")
def funil_novo(titulo: str = Form(...), tipo_servico: str = Form("filmagem"),
               company_id: str = Form(""), valor: str = Form(""), data_evento: str = Form("")):
    db.exec_("""INSERT INTO deal (titulo, tipo_servico, company_id, valor_estimado, data_evento)
                VALUES (%s, %s, NULLIF(%s,'')::uuid, NULLIF(%s,'')::numeric, NULLIF(%s,'')::date)""",
             (titulo.strip(), tipo_servico, company_id, valor, data_evento))
    return RedirectResponse("/funil", 303)


@app.post("/funil/{did}/estagio")
def funil_estagio(did: str, estagio: str = Form(...), motivo: str = Form("")):
    if estagio == "perdido" and not motivo.strip():
        return RedirectResponse("/funil?erro=Motivo+da+perda+é+obrigatório", 303)
    db.exec_("UPDATE deal SET estagio=%s, motivo_perda=NULLIF(%s,'') WHERE id=%s",
             (estagio, motivo.strip(), did))
    db.exec_("""INSERT INTO activity (entidade_tipo, entidade_id, tipo, conteudo, autor)
                VALUES ('deal', %s, 'evento_sistema', %s, 'humano')""",
             (did, f"movido para {estagio}" + (f" — {motivo}" if motivo.strip() else "")))
    return RedirectResponse("/funil", 303)


# -------------------------------------------------------------- projetos

@app.get("/projetos", response_class=HTMLResponse)
def projetos(request: Request):
    linhas = db.q("""SELECT p.*, co.nome AS empresa,
                            count(DISTINCT sd.id) AS diarias,
                            count(DISTINCT mo.id) AS offloads
                       FROM project p
                       LEFT JOIN company co ON co.id = p.company_id
                       LEFT JOIN shoot_day sd ON sd.project_id = p.id
                       LEFT JOIN media_offload mo ON mo.project_id = p.id
                      GROUP BY p.id, co.nome ORDER BY p.criado_em DESC""")
    return pag(request, "projetos.html", ativo="projetos", linhas=linhas,
               empresas=db.q("SELECT id, nome FROM company ORDER BY nome"))


@app.post("/projetos/novo")
def projeto_novo(nome: str = Form(...), slug: str = Form(...), company_id: str = Form(""),
                 valor_contrato: str = Form(""), data_entrega: str = Form("")):
    db.exec_("""INSERT INTO project (nome, slug, company_id, valor_contrato, data_entrega)
                VALUES (%s, %s, NULLIF(%s,'')::uuid, NULLIF(%s,'')::numeric, NULLIF(%s,'')::date)
                ON CONFLICT (slug) DO NOTHING""",
             (nome.strip(), slug.strip().lower(), company_id, valor_contrato, data_entrega))
    return RedirectResponse("/projetos", 303)


# --------------------------------------------------------------- agentes

@app.get("/agentes", response_class=HTMLResponse)
def agentes(request: Request):
    return pag(request, "agentes.html", ativo="agentes",
               pendentes=db.q("""SELECT * FROM approval_request WHERE status='pendente'
                                  ORDER BY criado_em DESC"""),
               execucoes=db.q("""SELECT ar.*, count(aa.*) acoes FROM agent_run ar
                                 LEFT JOIN agent_action aa ON aa.run_id = ar.id
                                 GROUP BY ar.id ORDER BY ar.iniciado_em DESC LIMIT 20"""))


@app.post("/agentes/aprovacao/{aid}")
def aprovacao(aid: str, decisao: str = Form(...)):
    novo = "aprovado" if decisao == "sim" else "rejeitado"
    a = db.q1("""UPDATE approval_request SET status=%s, decidido_por='humano', decidido_em=now()
                  WHERE id=%s AND status='pendente' RETURNING payload, descricao""", (novo, aid))
    # Aprovar uma mensagem = ela entra na outbox já autorizada. O envio em si acontece
    # quando houver canal configurado (e-mail/WhatsApp) — nada sai por baixo dos panos.
    if a and novo == "aprovado":
        p = a["payload"] if isinstance(a["payload"], dict) else {}
        if p.get("acao") == "enviar_mensagem":
            db.exec_("""INSERT INTO outbox (canal, destino, corpo, aprovado_por)
                        VALUES (%s, %s, %s, 'humano')""",
                     (p.get("canal", "whatsapp"), p.get("destinatario", "a definir"),
                      p.get("corpo", a["descricao"])))
    return RedirectResponse("/agentes", 303)


# ------------------------------------------------------ agentes: ações

@app.post("/agentes/rental/rodar")
def rental_rodar_agora():
    from .agentes import rental as ag_rental
    resumo = ag_rental.rodar()
    return RedirectResponse("/agentes", 303)


@app.post("/api/agentes/comercial/qualificar")
def api_qualificar(dados: dict):
    """Entrada de lead (WhatsApp/Instagram/site → webhook). O agente extrai, cria contato e
    negócio, e devolve um rascunho que fica AGUARDANDO APROVAÇÃO — nada é enviado daqui."""
    from .agentes import comercial as ag_comercial
    if not dados.get("mensagem"):
        return JSONResponse({"ok": False, "erro": "campo 'mensagem' é obrigatório"}, 400)
    if not ag_comercial.configurado():
        return JSONResponse({"ok": False,
                             "erro": "ANTHROPIC_API_KEY não configurada no serviço",
                             "dica": "Railway → duckstudios → Variables → ANTHROPIC_API_KEY"},
                            503)
    try:
        return ag_comercial.qualificar(
            mensagem=dados["mensagem"], nome=dados.get("nome"),
            telefone=dados.get("telefone"), canal=dados.get("canal", "whatsapp"))
    except Exception as e:                                           # noqa: BLE001
        return JSONResponse({"ok": False, "erro": f"{type(e).__name__}: {e}"}, 500)


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
