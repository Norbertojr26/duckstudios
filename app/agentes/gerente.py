"""Agente Gerente — garante as entregas e verifica cada solicitação.

100% código, zero LLM: cobrança de pendência não é opinião. A cada passada ele varre o
que está PARADO na casa e aponta, com nome e idade:
  * aprovações esperando o dono há mais de 24 h;
  * reações de evento que falharam nas últimas 24 h;
  * propostas enviadas há 7+ dias sem resposta do cliente;
  * tarefas de máquina paradas na fila há mais de 1 h;
  * máquinas com pastas autorizadas que sumiram há mais de 1 dia.

O resultado vira evento `gerente.verificacao` no barramento (visível na Sala) e fica na
auditoria. O gerente não executa nada em nome de ninguém — ele aponta; quem age é você.
"""
from . import barramento
from .. import db
from .registro import execucao

AGENTE = "gerente"


def _q(sql):
    try:
        return db.q(sql)
    except Exception:                                                # noqa: BLE001
        return []


def verificar():
    with execucao(AGENTE, "SOP-007", "agenda:verificacao") as ex:
        achados = []

        aprov = _q("""SELECT titulo, extract(epoch FROM now() - criado_em)/3600 AS h
                        FROM approval_request WHERE status = 'pendente'
                         AND criado_em < now() - interval '24 hours'
                       ORDER BY criado_em LIMIT 5""")
        for a in aprov:
            achados.append(f"aprovação parada há {int(a['h'])}h: {a['titulo'][:70]}")

        falhas = _q("""SELECT tipo, reacoes FROM evento
                        WHERE criado_em > now() - interval '24 hours'
                          AND reacoes::text LIKE '%%"ok": false%%' LIMIT 8""")
        for f in falhas:
            erro = next((r.get("erro", "") for r in f["reacoes"] if not r.get("ok")), "")
            achados.append(f"reação falhou em {f['tipo']}: {erro[:70]}")

        prop = _q("""SELECT numero, extract(epoch FROM now() - criado_em)/86400 AS d
                       FROM quote WHERE status = 'enviada'
                        AND criado_em < now() - interval '7 days'
                      ORDER BY criado_em LIMIT 5""")
        for p in prop:
            achados.append(f"proposta {p['numero']} enviada há {int(p['d'])}d sem resposta "
                           "— vale um follow-up")

        jobs = _q("""SELECT tipo, status FROM job_queue
                      WHERE tipo LIKE 'mac:%%' AND status IN ('pendente','processando')
                        AND criado_em < now() - interval '1 hour' LIMIT 5""")
        for j in jobs:
            achados.append(f"tarefa de máquina travada ({j['tipo']} · {j['status']}) — "
                           "a máquina está ligada?")

        maqs = _q("""SELECT m.nome FROM maquina m
                      WHERE m.ultimo_heartbeat < now() - interval '1 day'
                        AND EXISTS (SELECT 1 FROM maquina_pasta p
                                     WHERE p.maquina_id = m.id AND p.ativo) LIMIT 5""")
        for m in maqs:
            achados.append(f"máquina {m['nome']} sumida há 1+ dia com pastas autorizadas")

        resumo = {"achados": len(achados), "itens": achados[:12]}
        ex.acao("verificar_solicitacoes", {}, resumo, nivel="A4")
        if achados:
            barramento.emitir("gerente.verificacao", AGENTE, resumo)
        ex.concluir(saida=resumo)
        return resumo
