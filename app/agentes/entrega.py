"""Agente Entrega — a parte do Módulo 5 que não depende de credencial externa.

Duas vigias determinísticas, uma passada por dia:
1. Prazo de entregável estourando (D-2) ou estourado — aviso interno para você reconhecer.
2. Projeto entregue (roxo) há mais de N dias — hora de limpar o Drive. O upload espelha a
   estrutura local (docs/19), então a limpeza libera espaço sem perder nada: o backup
   definitivo é o storage local. Aprovar registra a decisão; a deleção em si continua manual
   até existir credencial do Drive.
"""
import json
import os

from .. import db
from .registro import execucao

AGENTE = "entrega"
DIAS_DRIVE = int(os.environ.get("ENTREGA_DIAS_DRIVE", "15"))


def _ja_pedido(tipo, chave_id):
    return db.q1("""SELECT 1 FROM approval_request
                     WHERE payload->>'tipo' = %s AND payload->>'ref' = %s
                       AND criado_em > now() - interval '7 days'""", (tipo, str(chave_id)))


def rodar():
    with execucao(AGENTE, "SOP-005", "agenda") as ex:
        criadas = 0

        em_risco = db.q("""
            SELECT d.id, d.nome, d.prazo, p.nome AS projeto,
                   (d.prazo < current_date) AS estourado
              FROM deliverable d JOIN project p ON p.id = d.project_id
             WHERE d.status NOT IN ('aprovado', 'entregue')
               AND d.prazo IS NOT NULL AND d.prazo <= current_date + 2
             ORDER BY d.prazo""")
        for d in em_risco:
            if _ja_pedido("prazo_entrega", d["id"]):
                continue
            rotulo = "ESTOUROU" if d["estourado"] else "vence em ≤2 dias"
            db.exec_("""INSERT INTO approval_request (run_id, titulo, descricao, payload)
                        VALUES (%s, %s, %s, %s)""",
                     (ex.id, f"⏰ Prazo {rotulo} — {d['nome']} ({d['projeto']})",
                      f"Entregável '{d['nome']}' do projeto {d['projeto']} com prazo "
                      f"{d['prazo'].strftime('%d/%m')} ainda não está aprovado. "
                      f"Aprovar = estou ciente e tratando.",
                      json.dumps({"acao": "reconhecer", "tipo": "prazo_entrega",
                                  "ref": str(d["id"])}, ensure_ascii=False)))
            criadas += 1

        # Roxo há mais de N dias: a data da transição vem do histórico, não de adivinhação.
        limpar = db.q("""
            SELECT p.id, p.nome, max(a.criado_em) AS entregue_em
              FROM project p JOIN activity a
                ON a.entidade_tipo = 'project' AND a.entidade_id = p.id
               AND a.conteudo LIKE %s
             WHERE p.estado_editorial = 'entregue'
               AND NOT EXISTS (SELECT 1 FROM activity x
                                WHERE x.entidade_tipo = 'project' AND x.entidade_id = p.id
                                  AND x.conteudo = 'drive marcado para limpeza')
             GROUP BY p.id
            HAVING max(a.criado_em) < now() - make_interval(days => %s)""",
            ("%→ entregue%", DIAS_DRIVE))
        for p in limpar:
            if _ja_pedido("limpar_drive", p["id"]):
                continue
            db.exec_("""INSERT INTO approval_request (run_id, titulo, descricao, payload)
                        VALUES (%s, %s, %s, %s)""",
                     (ex.id, f"🧹 Limpar Drive — {p['nome']} (entregue há {DIAS_DRIVE}+ dias)",
                      f"O projeto {p['nome']} está entregue desde "
                      f"{p['entregue_em'].strftime('%d/%m')}. O backup definitivo é o storage "
                      f"local; o Drive pode ser limpo para liberar cota.",
                      json.dumps({"acao": "limpar_drive", "tipo": "limpar_drive",
                                  "ref": str(p["id"]), "project_id": str(p["id"])},
                                 ensure_ascii=False)))
            criadas += 1

        resumo = {"prazos_em_risco": len(em_risco), "drives_a_limpar": len(limpar),
                  "avisos_criados": criadas}
        ex.acao("vigia_entregas", {}, resumo)
        ex.concluir(saida=resumo)
        return resumo
