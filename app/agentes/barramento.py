"""Barramento de eventos — o modelo de trabalho de TODOS os agentes.

Nada chama agente diretamente: tudo que acontece na casa vira uma linha na tabela
`evento` (o CRM é a memória), e cada agente ASSINA os tipos que lhe dizem respeito.
O despachante roda dentro do servidor e entrega os eventos pendentes aos assinantes,
em ordem de chegada — o que aconteceu, quem reagiu e com que resultado fica gravado
no próprio evento (coluna `reacoes`), visível na Sala.

Quem decide o que roda é a tabela ASSINATURAS abaixo — código, nunca um modelo.
As reações continuam passando pela auditoria de cada agente (registro.execucao),
e os tetos de autonomia não mudam: evento não é atalho para pular aprovação.

Tipos em uso (novos tipos: emita e assine aqui; evento sem assinante é só registro):
  agenda.tique          sistema, a cada 15 min — as rotinas assinam o tique
  email.recebido        secretaria, um por e-mail triado
  email.lead_recebido   secretaria → comercial qualifica
  lead.qualificado      comercial, ao fim da qualificação
  proposta.enviada/aceita/recusada   humano, na tela de propostas
  contrato.rascunho_criado           propostas, reação ao aceite
  aprovacao.concedida/negada         humano, na tela de aprovações
  maquina.conectada     sistema, primeiro heartbeat (ou volta após sumiço)
"""
import json
import traceback

from .. import db


def emitir(tipo, origem, payload=None):
    """Registrar que algo aconteceu; devolve o id (ou None). Nunca levanta exceção para
    quem emite: o evento é consequência do trabalho, não pré-condição — perder um evento
    não pode quebrar a ação."""
    try:
        r = db.q1("INSERT INTO evento (tipo, origem, payload) VALUES (%s, %s, %s) "
                  "RETURNING id",
                  (tipo, origem, json.dumps(payload or {}, ensure_ascii=False,
                                            default=str)))
        return str(r["id"])
    except Exception:                                                # noqa: BLE001
        print(f"[barramento] falha ao emitir {tipo}:\n" + traceback.format_exc())
        return None


def _rodou_hoje(agente, gatilho):
    return db.q1("""SELECT 1 FROM agent_run
                     WHERE agente = %s AND gatilho = %s
                       AND iniciado_em::date = current_date
                       AND status IN ('sucesso', 'em_progresso')""", (agente, gatilho))


# ------------------------------------------------------------------- reações
# Imports dentro das funções: o barramento é importado pelo main e pelos agentes,
# e imports tardios evitam ciclo.

def _ronda_rental(ev):
    from . import rental
    return rental.rodar()


def _reativacao_comercial(ev):
    from . import comercial
    if _rodou_hoje("comercial", "agenda:reativacao"):
        return "já rodou hoje"
    if not comercial.configurado():
        return "aguardando conexão Anthropic"
    return comercial.reativar()


def _prazos_entrega(ev):
    from . import entrega
    if _rodou_hoje("entrega", "agenda"):
        return "já rodou hoje"
    return entrega.rodar()


def _triagem_email(ev):
    from . import secretaria
    if not secretaria.configurado():
        return "aguardando conexão Gmail"
    return secretaria.triagem()


def _qualificar_lead_email(ev):
    from . import comercial
    p = ev["payload"]
    if not comercial.configurado():
        return "aguardando conexão Anthropic — lead fica registrado no evento"
    return comercial.qualificar(mensagem=p.get("mensagem", ""), nome=p.get("nome"),
                                canal=p.get("canal", "email"))


def _minuta_apos_aceite(ev):
    """Proposta aceita → minuta de contrato em RASCUNHO, determinística, para o humano
    revisar/completar/enviar. Nada sai da casa: rascunho é documento interno (A3)."""
    from .. import contratos
    qid = ev["payload"].get("quote_id")
    if not qid:
        return "evento sem quote_id"
    if db.q1("SELECT 1 FROM contrato WHERE quote_id = %s", (qid,)):
        return "já existe contrato para a proposta"
    q = db.q1("""SELECT q.*, d.titulo AS negocio, d.tipo_servico, d.data_evento,
                        co.nome AS empresa, c.nome AS contato_nome
                   FROM quote q LEFT JOIN deal d ON d.id = q.deal_id
                   LEFT JOIN company co ON co.id = d.company_id
                   LEFT JOIN contact c ON c.id = d.contact_id WHERE q.id = %s""", (qid,))
    if not q:
        return "proposta não encontrada"
    itens = db.q("SELECT * FROM quote_item WHERE quote_id = %s ORDER BY descricao", (qid,))
    ultimo = db.q1("SELECT contratada FROM contrato ORDER BY criado_em DESC LIMIT 1")
    contratada = (ultimo or {}).get("contratada") or \
        {"razao": "Duck Studios", "email": "duckcineproducoes@gmail.com"}
    contratante = {"razao": q["empresa"] or q["contato_nome"] or "",
                   "representante": q["contato_nome"] or ""}
    chave = contratos.SUGESTAO_POR_SERVICO.get(q["tipo_servico"] or "outro",
                                               "gravacao_edicao")
    titulo, corpo = contratos.montar(chave, q, itens, contratante, contratada)
    c = db.q1("""INSERT INTO contrato (quote_id, numero, template, titulo,
                                       contratante, contratada, corpo)
                 VALUES (%s, 'CT-'||to_char(now(),'YYMM')||'-'||
                            lpad((SELECT count(*)+1 FROM contrato)::text, 3, '0'),
                         %s, %s, %s, %s, %s) RETURNING id, numero""",
              (qid, chave, titulo,
               json.dumps(contratante, ensure_ascii=False),
               json.dumps(contratada, ensure_ascii=False), corpo))
    emitir("contrato.rascunho_criado", "propostas",
           {"contrato_id": str(c["id"]), "numero": c["numero"], "quote_id": str(qid)})
    return f"minuta {c['numero']} criada em rascunho — revisar dados do contratante"


def _tarefa_delegada(ev):
    """Tarefa/pergunta delegada pelo dono na Sala. O destino já foi decidido pelo
    roteador; aqui só se entrega à mesa certa — pipelines nativos executam o de sempre,
    agente admitido responde dentro da missão."""
    p = ev["payload"]
    destino, texto = p.get("destino", ""), p.get("texto", "")
    if not (destino and texto):
        return "evento sem destino/texto"
    if destino == "comercial":
        from . import comercial
        r = comercial.qualificar(mensagem=texto, canal="sala")
        return f"lead qualificado ({r['ramo']}) — rascunho aguardando aprovação"
    if destino == "propostas":
        from . import propostas
        r = propostas.proposta_por_voz(texto)
        return f"proposta em rascunho para {r['cliente']} — /propostas/{r['quote_id']}"
    if destino == "rental":
        from . import rental
        return rental.rodar()
    if destino == "entrega":
        from . import entrega
        return entrega.rodar()
    if destino == "secretaria":
        return _triagem_email(ev)
    from . import custom
    r = custom.responder(destino, texto)
    resumo = r["resposta"]
    if r.get("precisa_de_humano"):
        resumo += f"\n[precisa de você: {r['precisa_de_humano']}]"
    return resumo


ASSINATURAS = {
    "agenda.tique": [("rental", _ronda_rental),
                     ("comercial", _reativacao_comercial),
                     ("entrega", _prazos_entrega),
                     ("secretaria", _triagem_email)],
    "email.lead_recebido": [("comercial", _qualificar_lead_email)],
    "proposta.aceita": [("propostas", _minuta_apos_aceite)],
    "tarefa.delegada": [("expediente", _tarefa_delegada)],
}


def despachar(limite=25, so_evento=None):
    """Uma passada: entrega os eventos pendentes aos assinantes, mais antigos primeiro.
    O claim é atômico (UPDATE ... SKIP LOCKED): o laço do servidor e um despacho inline
    da delegação nunca pegam o mesmo evento. Reação que falha não trava a fila."""
    filtro, params = "", (limite,)
    if so_evento:
        filtro, params = "AND id = %s", (so_evento, limite)
    pendentes = db.q(f"""UPDATE evento SET processado_em = now()
                          WHERE id IN (SELECT id FROM evento
                                        WHERE processado_em IS NULL {filtro}
                                        ORDER BY criado_em LIMIT %s
                                        FOR UPDATE SKIP LOCKED)
                          RETURNING id, tipo, origem, payload""", params)
    for ev in pendentes:
        reacoes = []
        for agente, fn in ASSINATURAS.get(ev["tipo"], []):
            try:
                r = fn(ev)
                resumo = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False,
                                                                 default=str)
                reacoes.append({"agente": agente, "ok": True, "resumo": resumo[:400]})
            except Exception as e:                                   # noqa: BLE001
                reacoes.append({"agente": agente, "ok": False,
                                "erro": f"{type(e).__name__}: {e}"[:400]})
                print(f"[barramento] {agente} falhou em {ev['tipo']}:\n"
                      + traceback.format_exc())
        db.exec_("UPDATE evento SET reacoes = %s WHERE id = %s",
                 (json.dumps(reacoes, ensure_ascii=False), ev["id"]))
    return len(pendentes)
