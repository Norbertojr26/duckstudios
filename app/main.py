"""Duck Studios — CRM de patrimônio e locação.

Toda tela tem par em /api. A interface e os agentes leem a mesma base pelas mesmas consultas:
não existe número na tela que um agente não consiga buscar.
"""
import base64, json, os, secrets, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import auth, db
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
# Duas portas para o mesmo prédio: sessão de navegador (login por e-mail e senha, com
# papéis) para pessoas, e Basic auth (APP_USUARIO/APP_SENHA) para o que é máquina — o
# runtime do Mac, os agentes, curl. Basic equivale a papel dev; revogar sessão = apagar a
# linha em `sessao`.
USUARIO = os.environ.get("APP_USUARIO", "duck")
SENHA = os.environ.get("APP_SENHA", "")
LIVRE = ("/healthz", "/static", "/login", "/convite")
# Diretor usa a plataforma inteira, menos o que é desenvolvimento:
SO_DEV = ("/usuarios", "/api/docs", "/api/redoc", "/api/openapi.json")


def _basic_ok(request: Request) -> bool:
    cab = request.headers.get("authorization", "")
    if not cab.startswith("Basic "):
        return False
    try:
        u, _, p = base64.b64decode(cab[6:]).decode().partition(":")
        return secrets.compare_digest(u, USUARIO) and secrets.compare_digest(p, SENHA)
    except Exception:                                        # noqa: BLE001
        return False


def _usuario_da_sessao(request: Request):
    token = request.cookies.get("duck_sessao", "")
    if not token:
        return None
    try:
        return db.q1("""SELECT u.id, u.nome, u.email, u.papel,
                               (u.foto IS NOT NULL) AS tem_foto
                          FROM sessao s JOIN usuario u ON u.id = s.usuario_id
                         WHERE s.token = %s AND s.expira_em > now() AND u.ativo""",
                     (token,))
    except Exception:                                        # noqa: BLE001
        return None


@app.middleware("http")
async def exigir_acesso(request: Request, call_next):
    caminho = request.url.path
    request.state.usuario = None
    if not SENHA or caminho.startswith(LIVRE):
        return await call_next(request)
    if _basic_ok(request):
        request.state.usuario = {"id": None, "nome": "api", "papel": "dev", "tem_foto": False}
        return await call_next(request)
    u = _usuario_da_sessao(request)
    if u:
        request.state.usuario = dict(u)
        if u["papel"] != "dev" and caminho.startswith(SO_DEV):
            return RedirectResponse("/", 303)
        return await call_next(request)
    if caminho.startswith("/api/"):
        return Response(status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="Duck Studios"'})
    return RedirectResponse("/login", 303)


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
    return tpl.TemplateResponse(request, nome, {**ctx, "sem_senha": not SENHA,
                                                "usuario": getattr(request.state,
                                                                   "usuario", None)})


# ----------------------------------------------------- login, convite, perfil

DIAS_SESSAO = 30


def _abrir_sessao(resposta, request, usuario_id):
    token = auth.novo_token()
    db.exec_("INSERT INTO sessao (token, usuario_id, expira_em) "
             "VALUES (%s, %s, now() + make_interval(days => %s))",
             (token, usuario_id, DIAS_SESSAO))
    resposta.set_cookie("duck_sessao", token, max_age=DIAS_SESSAO * 86400,
                        httponly=True, samesite="lax",
                        secure=request.url.scheme == "https")
    return resposta


@app.get("/login", response_class=HTMLResponse)
def login(request: Request, erro: str = ""):
    if not SENHA or _usuario_da_sessao(request):
        return RedirectResponse("/", 303)
    return pag(request, "login.html", erro=erro)


@app.post("/login")
def login_post(request: Request, email: str = Form(...), senha: str = Form(...)):
    u = db.q1("SELECT id, senha_hash FROM usuario WHERE lower(email) = lower(%s) AND ativo",
              (email.strip(),))
    if not u or not auth.conferir(senha, u["senha_hash"]):
        import time
        time.sleep(0.6)                       # freio barato contra tentativa e erro
        return RedirectResponse("/login?erro=1", 303)
    return _abrir_sessao(RedirectResponse("/", 303), request, u["id"])


@app.post("/sair")
def sair(request: Request):
    token = request.cookies.get("duck_sessao", "")
    if token:
        db.exec_("DELETE FROM sessao WHERE token = %s", (token,))
    r = RedirectResponse("/login", 303)
    r.delete_cookie("duck_sessao")
    return r


@app.get("/convite/{token}", response_class=HTMLResponse)
def convite(request: Request, token: str):
    u = db.q1("SELECT nome, email FROM usuario WHERE convite_token = %s AND ativo", (token,))
    return pag(request, "convite.html", convidado=u, token=token)


@app.post("/convite/{token}")
def convite_post(request: Request, token: str, nome: str = Form(...),
                 senha: str = Form(...), senha2: str = Form(...)):
    u = db.q1("SELECT id FROM usuario WHERE convite_token = %s AND ativo", (token,))
    if not u:
        return RedirectResponse("/login", 303)
    if len(senha) < 8 or senha != senha2:
        return RedirectResponse(f"/convite/{token}?erro=1", 303)
    db.exec_("""UPDATE usuario SET nome = %s, senha_hash = %s, convite_token = NULL
                 WHERE id = %s""", (nome.strip(), auth.gerar_hash(senha), u["id"]))
    return _abrir_sessao(RedirectResponse("/", 303), request, u["id"])


def _eu(request):
    u = getattr(request.state, "usuario", None)
    return u if u and u.get("id") else None


@app.get("/perfil", response_class=HTMLResponse)
def perfil(request: Request, ok: str = "", erro: str = ""):
    eu = _eu(request)
    if not eu:
        return RedirectResponse("/", 303)
    completo = db.q1("SELECT id, nome, email, papel, (foto IS NOT NULL) AS tem_foto, "
                     "criado_em FROM usuario WHERE id = %s", (eu["id"],))
    sessoes = db.q1("SELECT count(*) AS n FROM sessao WHERE usuario_id = %s "
                    "AND expira_em > now()", (eu["id"],))["n"]
    return pag(request, "perfil.html", ativo="perfil", eu=completo, sessoes=sessoes,
               ok=ok, erro=erro)


@app.post("/perfil")
def perfil_post(request: Request, nome: str = Form(...), email: str = Form(...)):
    eu = _eu(request)
    if not eu:
        return RedirectResponse("/", 303)
    ja = db.q1("SELECT 1 FROM usuario WHERE lower(email) = lower(%s) AND id <> %s",
               (email.strip(), eu["id"]))
    if ja:
        return RedirectResponse("/perfil?erro=email", 303)
    db.exec_("UPDATE usuario SET nome = %s, email = %s WHERE id = %s",
             (nome.strip(), email.strip(), eu["id"]))
    return RedirectResponse("/perfil?ok=dados", 303)


@app.post("/perfil/senha")
def perfil_senha(request: Request, atual: str = Form(...), nova: str = Form(...),
                 nova2: str = Form(...)):
    eu = _eu(request)
    if not eu:
        return RedirectResponse("/", 303)
    g = db.q1("SELECT senha_hash FROM usuario WHERE id = %s", (eu["id"],))
    if not auth.conferir(atual, g["senha_hash"]):
        return RedirectResponse("/perfil?erro=atual", 303)
    if len(nova) < 8 or nova != nova2:
        return RedirectResponse("/perfil?erro=nova", 303)
    db.exec_("UPDATE usuario SET senha_hash = %s WHERE id = %s",
             (auth.gerar_hash(nova), eu["id"]))
    # troca de senha derruba as OUTRAS sessões — a atual continua
    db.exec_("DELETE FROM sessao WHERE usuario_id = %s AND token <> %s",
             (eu["id"], request.cookies.get("duck_sessao", "")))
    return RedirectResponse("/perfil?ok=senha", 303)


@app.post("/perfil/foto")
async def perfil_foto(request: Request, foto: UploadFile = File(...)):
    eu = _eu(request)
    if not eu:
        return RedirectResponse("/", 303)
    if not (foto.content_type or "").startswith("image/"):
        return RedirectResponse("/perfil?erro=foto", 303)
    corpo = await foto.read()
    if len(corpo) > 3_000_000:
        return RedirectResponse("/perfil?erro=foto", 303)
    db.exec_("UPDATE usuario SET foto = %s, foto_tipo = %s WHERE id = %s",
             (corpo, foto.content_type, eu["id"]))
    return RedirectResponse("/perfil?ok=foto", 303)


@app.get("/perfil/foto/{uid}")
def perfil_foto_ver(uid: str):
    u = db.q1("SELECT foto, foto_tipo FROM usuario WHERE id = %s", (uid,))
    if not u or not u["foto"]:
        return Response(status_code=404)
    return Response(bytes(u["foto"]), media_type=u["foto_tipo"] or "image/jpeg",
                    headers={"Cache-Control": "private, max-age=300"})


# ------------------------------------------------ usuários (só papel dev)

def _sou_dev(request):
    u = getattr(request.state, "usuario", None)
    return (not SENHA) or (u or {}).get("papel") == "dev"


@app.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request):
    if not _sou_dev(request):
        return RedirectResponse("/", 303)
    linhas = db.q("""SELECT id, nome, email, papel, ativo, convite_token,
                            (senha_hash IS NOT NULL) AS tem_senha,
                            (foto IS NOT NULL) AS tem_foto, criado_em
                       FROM usuario ORDER BY criado_em""")
    return pag(request, "usuarios.html", ativo="usuarios", linhas=linhas,
               base=str(request.base_url).rstrip("/"))


@app.post("/usuarios")
def usuarios_post(request: Request, nome: str = Form(...), email: str = Form(...),
                  papel: str = Form("diretor")):
    if not _sou_dev(request):
        return RedirectResponse("/", 303)
    db.exec_("""INSERT INTO usuario (nome, email, papel, convite_token)
                VALUES (%s, %s, %s, %s) ON CONFLICT (email) DO NOTHING""",
             (nome.strip(), email.strip(),
              papel if papel in ("dev", "diretor") else "diretor", auth.novo_token()))
    return RedirectResponse("/usuarios", 303)


@app.post("/usuarios/{uid}/convite")
def usuarios_convite(request: Request, uid: str):
    """(Re)gera o link — serve para convite perdido e para redefinir senha."""
    if not _sou_dev(request):
        return RedirectResponse("/", 303)
    db.exec_("UPDATE usuario SET convite_token = %s WHERE id = %s",
             (auth.novo_token(), uid))
    return RedirectResponse("/usuarios", 303)


@app.post("/usuarios/{uid}/ativo")
def usuarios_ativo(request: Request, uid: str):
    if not _sou_dev(request):
        return RedirectResponse("/", 303)
    eu = _eu(request)
    if eu and str(eu["id"]) == uid:
        return RedirectResponse("/usuarios", 303)          # ninguém se tranca para fora
    db.exec_("UPDATE usuario SET ativo = NOT ativo WHERE id = %s", (uid,))
    db.exec_("""DELETE FROM sessao s USING usuario u
                 WHERE s.usuario_id = u.id AND u.id = %s AND NOT u.ativo""", (uid,))
    return RedirectResponse("/usuarios", 303)


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
               estados=ESTADOS_EDITORIAIS,
               empresas=db.q("SELECT id, nome FROM company ORDER BY nome"))


@app.post("/projetos/novo")
def projeto_novo(nome: str = Form(...), slug: str = Form(...), company_id: str = Form(""),
                 valor_contrato: str = Form(""), data_entrega: str = Form("")):
    db.exec_("""INSERT INTO project (nome, slug, company_id, valor_contrato, data_entrega)
                VALUES (%s, %s, NULLIF(%s,'')::uuid, NULLIF(%s,'')::numeric, NULLIF(%s,'')::date)
                ON CONFLICT (slug) DO NOTHING""",
             (nome.strip(), slug.strip().lower(), company_id, valor_contrato, data_entrega))
    return RedirectResponse("/projetos", 303)


ESTADOS_EDITORIAIS = {          # o fluxo real do Finder, cor a cor
    "ingerido":  {"rotulo": "não iniciado", "cor": "#F87171", "finder": "Red"},
    "em_edicao": {"rotulo": "em edição",    "cor": "#FBBF24", "finder": "Yellow"},
    "aprovado":  {"rotulo": "aprovado",     "cor": "#4ADE80", "finder": "Green"},
    "entregue":  {"rotulo": "no Drive",     "cor": "#C084FC", "finder": "Purple"},
}


@app.post("/projetos/{pid}/estado")
def projeto_estado(pid: str, estado: str = Form(...)):
    if estado not in ESTADOS_EDITORIAIS:
        return RedirectResponse("/projetos", 303)
    db.exec_("UPDATE project SET estado_editorial=%s WHERE id=%s", (estado, pid))
    db.exec_("""INSERT INTO activity (entidade_tipo, entidade_id, tipo, conteudo, autor)
                VALUES ('project', %s, 'evento_sistema', %s, 'humano')""",
             (pid, f"estado editorial → {estado}"))
    return RedirectResponse("/projetos", 303)


@app.get("/api/projetos")
def api_projetos():
    """Lista para o refletor de tags no Mac: slug (nome da pasta) + estado + cor do Finder."""
    return [{**p, "finder": ESTADOS_EDITORIAIS[p["estado_editorial"]]["finder"]}
            for p in db.q("""SELECT slug, nome, estado_editorial, pasta_raiz
                               FROM project WHERE status = 'ativo' ORDER BY slug""")]


@app.post("/api/projetos/{slug}/estado")
def api_projeto_estado(slug: str, dados: dict):
    """Transição vinda do Mac (o editor mudou a tag na pasta). A tag é INTERFACE de entrada;
    a verdade continua sendo o banco — e a mudança fica registrada com origem."""
    estado = dados.get("estado")
    if estado not in ESTADOS_EDITORIAIS:
        return JSONResponse({"ok": False, "erro": f"estado deve ser um de "
                             f"{list(ESTADOS_EDITORIAIS)}"}, 400)
    p = db.q1("UPDATE project SET estado_editorial=%s WHERE slug=%s RETURNING id, nome",
              (estado, slug))
    if not p:
        return JSONResponse({"ok": False, "erro": f"projeto '{slug}' não existe"}, 404)
    db.exec_("""INSERT INTO activity (entidade_tipo, entidade_id, tipo, conteudo, autor)
                VALUES ('project', %s, 'evento_sistema', %s, 'mac:finder-tag')""",
             (p["id"], f"estado editorial → {estado} (tag mudada no Finder)"))
    return {"ok": True, "projeto": p["nome"], "estado": estado}


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
        elif p.get("acao") == "limpar_drive" and p.get("project_id"):
            db.exec_("""INSERT INTO activity (entidade_tipo, entidade_id, tipo, conteudo, autor)
                        VALUES ('project', %s, 'evento_sistema',
                                'drive marcado para limpeza', 'humano')""",
                     (p["project_id"],))
        elif p.get("acao") == "liberar_formatacao" and p.get("offload_id"):
            db.exec_("UPDATE media_offload SET liberado_para_format = true WHERE id = %s",
                     (p["offload_id"],))
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


# ----------------------------------------------------- máquinas (Mac Mini)

TAREFAS_MAC = ("inventariar_pastas", "refletir_tags", "capturar_tags",
               "criar_job", "mover", "enviar_lixeira")
# Campos que cada tarefa de escrita exige — o formulário vira payload fechado; quem valida
# caminho contra a allowlist é o runtime no Mac, na hora de executar.
CAMPOS_MAC = {"criar_job": ("cliente", "job"), "mover": ("origem", "destino"),
              "enviar_lixeira": ("caminho",)}


@app.get("/maquinas", response_class=HTMLResponse)
def maquinas(request: Request):
    linhas = db.q("""SELECT m.*, (m.ultimo_heartbeat > now() - interval '3 minutes') AS online
                       FROM maquina m ORDER BY m.nome""")
    pastas = db.q("SELECT * FROM maquina_pasta WHERE ativo ORDER BY caminho")
    por_maquina = {}
    for p in pastas:
        por_maquina.setdefault(p["maquina_id"], []).append(p)
    tarefas = db.q("""SELECT id, tipo, payload, status, criado_em, erro FROM job_queue
                       WHERE tipo LIKE 'mac:%%' ORDER BY criado_em DESC LIMIT 12""")
    return pag(request, "maquinas.html", ativo="maquinas", linhas=linhas,
               por_maquina=por_maquina, tarefas=tarefas, tipos=TAREFAS_MAC[:3])


@app.post("/maquinas/pasta")
def maquina_pasta_add(maquina_id: str = Form(...), caminho: str = Form(...),
                      permissao: str = Form("leitura")):
    db.exec_("""INSERT INTO maquina_pasta (maquina_id, caminho, permissao)
                VALUES (%s, %s, %s)
                ON CONFLICT (maquina_id, caminho)
                DO UPDATE SET ativo = true, permissao = EXCLUDED.permissao""",
             (maquina_id, caminho.strip().rstrip("/"),
              permissao if permissao in ("leitura", "leitura_escrita") else "leitura"))
    return RedirectResponse("/maquinas", 303)


@app.post("/maquinas/pasta/{pid}/remover")
def maquina_pasta_rm(pid: str):
    db.exec_("UPDATE maquina_pasta SET ativo = false WHERE id = %s", (pid,))
    return RedirectResponse("/maquinas", 303)


@app.post("/maquinas/{mid}/tarefa")
def maquina_tarefa(mid: str, tipo: str = Form(...), cliente: str = Form(""),
                   job: str = Form(""), origem: str = Form(""), destino: str = Form(""),
                   caminho: str = Form("")):
    if tipo not in TAREFAS_MAC:
        return RedirectResponse("/maquinas", 303)
    extras = {"cliente": cliente, "job": job, "origem": origem,
              "destino": destino, "caminho": caminho}
    payload = {k: v.strip() for k, v in extras.items() if v.strip()}
    if any(c not in payload for c in CAMPOS_MAC.get(tipo, ())):
        return RedirectResponse("/maquinas", 303)
    m = db.q1("SELECT nome FROM maquina WHERE id = %s", (mid,))
    if m:
        db.exec_("INSERT INTO job_queue (tipo, payload) VALUES (%s, %s)",
                 (f"mac:{tipo}", json.dumps({**payload, "maquina": m["nome"]},
                                            ensure_ascii=False)))
    return RedirectResponse("/maquinas", 303)


# --- instalador de um clique: o CRM distribui o próprio runtime ---

ARQS_INSTALADOR = ("duck_mac.py", "refletir_tags.py", "duck_ingest.py")

# .command = duplo-clique abre no Terminal do macOS. Vai dentro de um .zip porque download
# de navegador perde o bit de execução — o Archive Utility preserva o do zip ao extrair.
_INSTALADOR = r"""#!/bin/bash
# Instalador da máquina Duck Studios — gerado pelo CRM (__URL__).
# O runtime só toca nas pastas autorizadas na tela Máquinas; nenhuma porta aberta no Mac.
set -euo pipefail
URL="__URL__"
echo "=== Duck Studios — conectar esta máquina ao CRM ==="
echo "CRM: $URL"
PADRAO="$(hostname -s | tr '[:upper:]' '[:lower:]')"
printf "Nome desta máquina [%s]: " "$PADRAO"; read NOME; NOME="${NOME:-$PADRAO}"
printf "Usuário do CRM [duck]: "; read USUARIO; USUARIO="${USUARIO:-duck}"
printf "Senha do CRM: "; read -s SENHA; echo

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "✕ python3 não encontrado. Rode:  xcode-select --install   e depois este instalador de novo."
  exit 1
fi

DEST="$HOME/DuckStudios/runtime"
mkdir -p "$DEST"
echo "→ baixando o runtime do CRM…"
for f in duck_mac.py refletir_tags.py duck_ingest.py; do
  curl -fsS -u "$USUARIO:$SENHA" "$URL/maquinas/instalador/arquivo/$f" -o "$DEST/$f" \
    || { echo "✕ falha ao baixar $f — a senha está certa?"; exit 1; }
done

echo "→ primeiro contato com o CRM…"
DUCK_URL="$URL" DUCK_USUARIO="$USUARIO" DUCK_SENHA="$SENHA" DUCK_MAQUINA="$NOME" \
  "$PY" "$DEST/duck_mac.py" --uma-vez \
  || { echo "✕ não conectou — confira usuário e senha e rode de novo"; exit 1; }

PLIST="$HOME/Library/LaunchAgents/br.com.duckstudios.mac.plist"
LOG="$HOME/Library/Logs/duck_mac.log"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<FIM
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>br.com.duckstudios.mac</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>$DEST/duck_mac.py</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>DUCK_URL</key><string>$URL</string>
    <key>DUCK_USUARIO</key><string>$USUARIO</string>
    <key>DUCK_SENHA</key><string>$SENHA</string>
    <key>DUCK_MAQUINA</key><string>$NOME</string>
  </dict>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
FIM
chmod 600 "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo
echo "✓ Pronto. '$NOME' fica conectada sempre que o Mac estiver ligado."
echo "  Autorize as pastas em: $URL/maquinas"
echo "  Log: $LOG"
echo "  Desinstalar: launchctl unload \"$PLIST\" && rm \"$PLIST\""
"""


def _instalador_corpo(request: Request) -> str:
    return _INSTALADOR.replace("__URL__", str(request.base_url).rstrip("/"))


@app.get("/maquinas/instalador")
def maquina_instalador(request: Request):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("instalar-duck-mac.command")
        zi.create_system = 3                      # unix: honra o modo de arquivo
        zi.external_attr = 0o755 << 16
        z.writestr(zi, _instalador_corpo(request))
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition":
                             'attachment; filename="instalar-duck-mac.zip"'})


@app.get("/maquinas/instalador.sh")
def maquina_instalador_sh(request: Request):
    """O mesmo instalador em texto puro, para quem prefere uma linha no Terminal."""
    return Response(_instalador_corpo(request), media_type="text/x-shellscript")


# Windows: PowerShell no lugar do bash, Tarefa Agendada no lugar do launchd. O runtime é o
# mesmo duck_mac.py — as tarefas exclusivas de macOS (tags do Finder) respondem erro claro.
_INSTALADOR_WIN = r"""# Instalador da maquina Duck Studios para Windows — gerado pelo CRM (__URL__).
# So toca nas pastas autorizadas na tela Maquinas; nenhuma porta aberta nesta maquina.
$ErrorActionPreference = "Stop"
$URL = "__URL__"
Write-Host "=== Duck Studios — conectar esta maquina ao CRM ==="
Write-Host "CRM: $URL"
$PADRAO = $env:COMPUTERNAME.ToLower()
$NOME = Read-Host "Nome desta maquina [$PADRAO]"
if (-not $NOME) { $NOME = $PADRAO }
$USUARIO = Read-Host "Usuario do CRM [duck]"
if (-not $USUARIO) { $USUARIO = "duck" }
$SEG = Read-Host "Senha do CRM" -AsSecureString
$SENHA = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
         [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SEG))

$PY = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PY) { $PY = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $PY) {
  Write-Host "x Python nao encontrado. Instale em https://www.python.org/downloads/"
  Write-Host "  (marque 'Add python.exe to PATH') e rode este instalador de novo."
  Read-Host "Enter para sair"; exit 1
}

$DEST = "$env:APPDATA\DuckStudios\runtime"
New-Item -ItemType Directory -Force -Path $DEST | Out-Null
$B64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("$($USUARIO):$SENHA"))
Write-Host "-> baixando o runtime do CRM..."
foreach ($f in @("duck_mac.py", "duck_ingest.py")) {
  Invoke-WebRequest -Headers @{Authorization = "Basic $B64"} `
    -Uri "$URL/maquinas/instalador/arquivo/$f" -OutFile "$DEST\$f"
}

Write-Host "-> primeiro contato com o CRM..."
$env:DUCK_URL = $URL; $env:DUCK_USUARIO = $USUARIO
$env:DUCK_SENHA = $SENHA; $env:DUCK_MAQUINA = $NOME
& $PY "$DEST\duck_mac.py" --uma-vez
if ($LASTEXITCODE -ne 0) {
  Write-Host "x Nao conectou — confira usuario e senha e rode de novo."
  Read-Host "Enter para sair"; exit 1
}

# .bat com as variaveis + .vbs para rodar sem janela; Tarefa Agendada dispara no logon.
$BAT = "$DEST\duck_mac.bat"
@"
@echo off
set DUCK_URL=$URL
set DUCK_USUARIO=$USUARIO
set DUCK_SENHA=$SENHA
set DUCK_MAQUINA=$NOME
"$PY" "$DEST\duck_mac.py" >> "$DEST\duck_mac.log" 2>&1
"@ | Set-Content -Path $BAT -Encoding ASCII
$VBS = "$DEST\duck_mac.vbs"
"CreateObject(""Wscript.Shell"").Run """"""$BAT"""""", 0, False" |
  Set-Content -Path $VBS -Encoding ASCII

$ACAO = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VBS`""
$GATILHO = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "DuckStudiosMaquina" -Action $ACAO `
  -Trigger $GATILHO -Force | Out-Null
Start-Process wscript.exe -ArgumentList "`"$VBS`""

Write-Host ""
Write-Host "OK — '$NOME' fica conectada sempre que voce fizer logon."
Write-Host "Autorize as pastas em: $URL/maquinas"
Write-Host "Log: $DEST\duck_mac.log"
Write-Host "Desinstalar: Unregister-ScheduledTask DuckStudiosMaquina"
Read-Host "Enter para fechar"
"""


@app.get("/maquinas/instalador.ps1")
def maquina_instalador_ps1(request: Request):
    corpo = _INSTALADOR_WIN.replace("__URL__", str(request.base_url).rstrip("/"))
    return Response(corpo, media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition":
                             'attachment; filename="instalar-duck-maquina.ps1"'})


@app.get("/maquinas/instalador/arquivo/{nome}")
def maquina_instalador_arquivo(nome: str):
    if nome not in ARQS_INSTALADOR:
        return JSONResponse({"erro": "arquivo desconhecido"}, 404)
    caminho = RAIZ.parent / "scripts" / "mac" / nome
    if not caminho.is_file():
        return JSONResponse({"erro": "runtime não disponível neste deploy"}, 404)
    return Response(caminho.read_text(), media_type="text/x-python")


# --- o lado que o runtime do Mac consome ---

@app.post("/api/mac/heartbeat")
def api_mac_heartbeat(dados: dict):
    """A máquina se apresenta e recebe de volta as pastas que PODE tocar. A lista mora aqui;
    a ponta só obedece — revogar acesso é remover a pasta na tela, sem tocar no Mac."""
    nome = (dados.get("maquina") or "").strip()
    if not nome:
        return JSONResponse({"ok": False, "erro": "campo 'maquina' obrigatório"}, 400)
    m = db.q1("""INSERT INTO maquina (nome, ultimo_heartbeat, info)
                 VALUES (%s, now(), %s)
                 ON CONFLICT (nome) DO UPDATE
                   SET ultimo_heartbeat = now(), info = EXCLUDED.info
                 RETURNING id""",
              (nome, json.dumps(dados.get("info", {}), ensure_ascii=False)))
    pastas = db.q("""SELECT caminho, permissao FROM maquina_pasta
                      WHERE maquina_id = %s AND ativo""", (m["id"],))
    return {"ok": True, "pastas": pastas}


@app.get("/api/mac/proxima-tarefa")
def api_mac_proxima(maquina: str):
    with db.cur() as c:
        c.execute("""SELECT id, tipo, payload FROM job_queue
                      WHERE tipo LIKE 'mac:%%' AND status = 'pendente'
                        AND payload->>'maquina' = %s
                      ORDER BY criado_em
                      FOR UPDATE SKIP LOCKED LIMIT 1""", (maquina,))
        t = c.fetchone()
        if not t:
            return {"tarefa": None}
        c.execute("UPDATE job_queue SET status='processando', tentativas=tentativas+1 "
                  "WHERE id=%s", (t["id"],))
        return {"tarefa": {"id": t["id"], "tipo": t["tipo"].removeprefix("mac:"),
                           "payload": t["payload"]}}


@app.post("/api/mac/resultado/{jid}")
def api_mac_resultado(jid: int, dados: dict):
    ok = bool(dados.get("ok"))
    db.exec_("""UPDATE job_queue SET status=%s, erro=%s, payload = payload || %s
                 WHERE id=%s""",
             ("concluido" if ok else "falha", dados.get("erro"),
              json.dumps({"resultado": dados.get("resultado")}, ensure_ascii=False, default=str),
              jid))
    from .agentes.registro import execucao
    with execucao("dit", "SOP-001", "tarefa:mac") as ex:
        ex.acao(dados.get("tipo", "tarefa_mac"), {"job": jid},
                dados.get("resultado") or {"erro": dados.get("erro")},
                erro=None if ok else (dados.get("erro") or "falha"))
    return {"ok": True}


# ------------------------------------------------------------ agente DIT

@app.post("/api/agentes/dit/offload")
def api_dit_offload(dados: dict):
    """O Mac registra um offload verificado. O CRM guarda offload+arquivos e abre a aprovação
    de liberação do cartão — quem formata é humano, na câmera, depois de aprovar."""
    from .agentes.registro import execucao
    obrigatorios = ("projeto", "camera", "card_uuid", "arquivos", "bytes", "destinos", "status")
    if any(k not in dados for k in obrigatorios):
        return JSONResponse({"ok": False, "erro": f"campos obrigatórios: {obrigatorios}"}, 400)
    proj = db.q1("SELECT id, nome FROM project WHERE slug = %s", (dados["projeto"],))
    if not proj:
        return JSONResponse({"ok": False, "erro": f"projeto '{dados['projeto']}' não existe — "
                             "crie em /projetos antes do offload"}, 404)

    with execucao("dit", "SOP-001", "offload:mac",
                  {"card_uuid": dados["card_uuid"], "camera": dados["camera"]}) as ex:
        off = db.q1("""SELECT id FROM media_offload
                        WHERE card_uuid = %s AND project_id = %s""",
                    (dados["card_uuid"], proj["id"]))
        if off:
            db.exec_("""UPDATE media_offload SET status=%s, arquivos_total=%s, bytes_total=%s,
                        destinos=%s, divergencias=%s, concluido_em=now(), trace_id=%s
                         WHERE id=%s""",
                     (dados["status"], dados["arquivos"], dados["bytes"],
                      json.dumps(dados["destinos"]), json.dumps(dados.get("divergencias", [])),
                      ex.trace_id, off["id"]))
            offload_id = off["id"]
        else:
            offload_id = db.q1("""INSERT INTO media_offload
                        (project_id, card_uuid, camera, status, arquivos_total, bytes_total,
                         destinos, divergencias, concluido_em, trace_id)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now(),%s) RETURNING id""",
                     (proj["id"], dados["card_uuid"], dados["camera"], dados["status"],
                      dados["arquivos"], dados["bytes"], json.dumps(dados["destinos"]),
                      json.dumps(dados.get("divergencias", [])), ex.trace_id))["id"]
        for f in dados.get("arquivos_detalhe", []):
            db.exec_("""INSERT INTO media_file (offload_id, caminho_relativo, nome_original,
                                                bytes, hash_xxh64)
                        VALUES (%s,%s,%s,%s,%s)
                        ON CONFLICT (offload_id, caminho_relativo) DO UPDATE
                          SET hash_xxh64 = EXCLUDED.hash_xxh64, bytes = EXCLUDED.bytes""",
                     (offload_id, f["rel"], f["nome"], f["bytes"], f["hash"]))
        ex.acao("registrar_offload",
                {"projeto": dados["projeto"], "camera": dados["camera"]},
                {"arquivos": dados["arquivos"],
                 "tamanho": (f"{dados['bytes']/1e9:.2f} GB" if dados["bytes"] >= 1e9
                             else f"{dados['bytes']/1e6:.0f} MB"),
                 "destinos": len(dados["destinos"]), "status": dados["status"]})

        if dados["status"] == "verificado":
            ja = db.q1("""SELECT 1 FROM approval_request WHERE payload->>'offload_id' = %s""",
                       (str(offload_id),))
            if not ja:
                db.exec_("""INSERT INTO approval_request (run_id, titulo, descricao, payload)
                            VALUES (%s, %s, %s, %s)""",
                         (ex.id,
                          f"💾 Liberar cartão para formatação — {proj['nome']} · "
                          f"{dados['camera']} {dados.get('card', '')}",
                          f"{dados['arquivos']} arquivos ({dados['bytes']/1e9:.1f} GB) "
                          f"verificados em {len(dados['destinos'])} destinos. Aprovar libera a "
                          f"formatação — que é feita por você, na câmera.",
                          json.dumps({"acao": "liberar_formatacao", "tipo": "liberar_formatacao",
                                      "offload_id": str(offload_id)}, ensure_ascii=False)))
                ex.acao("pedir_liberacao_formatacao", {}, {"offload_id": str(offload_id)},
                        nivel="A2")
        ex.concluir(saida={"offload_id": str(offload_id), "status": dados["status"]})
    return {"ok": True, "offload_id": str(offload_id), "status": dados["status"],
            "aprovacao": "liberação de formatação aguardando humano"
                          if dados["status"] == "verificado" else "com divergências — não liberar"}


@app.get("/fluxos", response_class=HTMLResponse)
def fluxos(request: Request):
    return pag(request, "fluxos.html", ativo="fluxos")


# --------------------------------------------------- agentes: sala ao vivo

# O "ambiente" dos agentes é o banco + a API: o mundo deles é o CRM. Esta sala torna esse
# trabalho visível — cada agente é uma mesa, cada tool call vira um evento na esteira.
MESAS = [
    {"chave": "rental", "nome": "Rental", "papel": "Régua de devoluções e atrasos",
     "sop": "SOP-002", "cor": "#60A5FA", "origem": "agendado"},
    {"chave": "comercial", "nome": "Comercial", "papel": "Qualificação de leads",
     "sop": "SOP-003", "cor": "#2DBDB8", "origem": "evento"},
    {"chave": "dit", "nome": "DIT / Mídia", "papel": "Ingestão e verificação de cartões",
     "sop": "SOP-001", "cor": "#FBBF24", "origem": "futuro",
     "motivo": "precisa do Mac Mini (acesso físico aos volumes)"},
    {"chave": "entrega", "nome": "Entrega", "papel": "Prazos e limpeza do Drive",
     "sop": "SOP-005", "cor": "#F87171", "origem": "agendado"},
]


@app.get("/agentes/sala", response_class=HTMLResponse)
def sala(request: Request):
    return pag(request, "sala.html", ativo="sala")


@app.get("/api/agentes/estado")
def api_agentes_estado():
    from .agentes import comercial as ag_comercial
    from .agentes.agenda import ATIVO, INTERVALO

    stats = {r["agente"]: r for r in db.q("""
        SELECT agente,
               count(*) FILTER (WHERE iniciado_em::date = current_date)          AS hoje,
               count(*) FILTER (WHERE status = 'em_progresso'
                                AND iniciado_em > now() - interval '10 minutes') AS ativos,
               max(iniciado_em)                                                   AS ultima,
               coalesce(sum(tokens_entrada) FILTER
                        (WHERE iniciado_em::date = current_date), 0)              AS tok_in,
               coalesce(sum(tokens_saida) FILTER
                        (WHERE iniciado_em::date = current_date), 0)              AS tok_out
          FROM agent_run GROUP BY agente""")}
    pendentes = {r["agente"]: r["n"] for r in db.q("""
        SELECT ar.agente, count(*) n
          FROM approval_request a JOIN agent_run ar ON ar.id = a.run_id
         WHERE a.status = 'pendente' GROUP BY ar.agente""")}
    feed = db.q("""
        SELECT aa.executado_em, ar.agente, aa.tool, aa.nivel_autonomia, aa.resultado, aa.erro
          FROM agent_action aa JOIN agent_run ar ON ar.id = aa.run_id
         ORDER BY aa.executado_em DESC LIMIT 20""")

    mesas = []
    for m in MESAS:
        st = stats.get(m["chave"], {})
        pend = pendentes.get(m["chave"], 0)
        if m["origem"] == "futuro" and not st:
            estado, detalhe = "futuro", m.get("motivo", "")
        elif m["origem"] == "futuro":
            estado, detalhe = "plantao", "recebendo offloads do Mac"
        elif m["chave"] == "comercial" and not ag_comercial.configurado():
            estado, detalhe = "sem_chave", "aguardando ANTHROPIC_API_KEY"
        elif st.get("ativos"):
            estado, detalhe = "trabalhando", "executando agora"
        elif pend:
            estado, detalhe = "aguardando", f"{pend} aprovação(ões) para você"
        else:
            estado = "plantao"
            if m["chave"] == "rental" and ATIVO and st.get("ultima"):
                from datetime import datetime, timezone
                falta = INTERVALO - (datetime.now(timezone.utc) - st["ultima"]).total_seconds()
                detalhe = (f"de plantão · próxima ronda em ~{max(1, int(falta // 60))} min"
                           if falta > 0 else "de plantão · ronda a caminho")
            elif m["origem"] == "agendado":
                detalhe = "de plantão · vigia diária"
            else:
                detalhe = "de plantão · acionado por evento"
        mesas.append({**m, "estado": estado, "detalhe": detalhe,
                      "hoje": st.get("hoje", 0), "pendentes": pend,
                      "ultima": st["ultima"].isoformat() if st.get("ultima") else None,
                      "tokens": (st.get("tok_in", 0) or 0) + (st.get("tok_out", 0) or 0)})
    return {"mesas": mesas,
            "feed": [{"quando": f["executado_em"].isoformat(), "agente": f["agente"],
                      "tool": f["tool"], "nivel": f["nivel_autonomia"],
                      "resultado": f["resultado"], "erro": f["erro"]} for f in feed]}


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
