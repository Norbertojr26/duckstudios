"""Agente Rental — a régua de notificações do Módulo 4 do SOP.

Inteiramente determinístico: as condições (devolve hoje, atrasou) são consultas SQL, e a
mensagem sai de template. Nada aqui precisa de LLM — e é de propósito: cobrança e prazo são
exatamente o tipo de coisa em que um modelo inventando frase só adiciona risco.

Autonomia A2: o agente REDIGE e pede aprovação; quem envia é humano. Aprovado, a mensagem
vai para a outbox e sai quando houver canal configurado (e-mail/WhatsApp).
"""
import json
from datetime import date

from .. import db
from .registro import execucao

AGENTE = "rental"


def _ja_pedido(rental_id, tipo_hoje):
    """Uma aprovação por saída por tipo por dia — reexecutar o agente não duplica pedido."""
    return db.q1("""SELECT 1 FROM approval_request
                     WHERE payload->>'rental_id' = %s AND payload->>'tipo' = %s
                       AND criado_em::date = current_date""", (str(rental_id), tipo_hoje))


def _pedir_aprovacao(ex, r, tipo, titulo, mensagem):
    if _ja_pedido(r["id"], tipo):
        return False
    db.exec_("""INSERT INTO approval_request (run_id, titulo, descricao, payload)
                VALUES (%s, %s, %s, %s)""",
             (ex.id, titulo, mensagem, json.dumps({
                 "acao": "enviar_mensagem", "rental_id": str(r["id"]), "tipo": tipo,
                 "destinatario": r["responsavel"], "canal": "whatsapp", "corpo": mensagem,
             }, ensure_ascii=False)))
    ex.acao("pedir_aprovacao", {"rental": r["numero"], "tipo": tipo},
            {"titulo": titulo}, nivel="A2")
    return True


def rodar():
    """Uma passada da régua. Idempotente — rodar de novo no mesmo dia não duplica nada."""
    with execucao(AGENTE, "SOP-002", "agenda") as ex:
        criados = 0

        devolve_hoje = db.q("""
            SELECT r.id, r.numero, r.previsao_devolucao,
                   coalesce(r.responsavel_nome, c.nome, co.nome) AS responsavel,
                   count(rl.*) AS itens
              FROM rental r
              JOIN rental_line rl ON rl.rental_id = r.id AND rl.status = 'em_campo'
              LEFT JOIN contact c ON c.id = r.contact_id
              LEFT JOIN company co ON co.id = r.company_id
             WHERE r.status = 'em_campo'
               AND r.previsao_devolucao::date = current_date
             GROUP BY r.id, c.nome, co.nome""")

        for r in devolve_hoje:
            hora = r["previsao_devolucao"].strftime("%H:%M")
            msg = (f"Olá, {r['responsavel']}! Lembramos que o período de locação dos seus "
                   f"{r['itens']} equipamentos encerra hoje. A devolução deve ser feita até "
                   f"às {hora} na sede da Duck Studios. Qualquer imprevisto, nos avise por aqui.")
            criados += _pedir_aprovacao(
                ex, r, "lembrete_devolucao",
                f"Lembrete de devolução — {r['responsavel']} (saída {r['numero']})", msg)

        atrasados = db.q("""
            SELECT r.id, r.numero, r.previsao_devolucao,
                   coalesce(r.responsavel_nome, c.nome, co.nome) AS responsavel,
                   count(rl.*) AS itens,
                   coalesce(sum(a.valor_reposicao), 0) AS exposicao,
                   (current_date - r.previsao_devolucao::date) AS dias
              FROM rental r
              JOIN rental_line rl ON rl.rental_id = r.id AND rl.status = 'em_campo'
              JOIN asset a ON a.id = rl.asset_id
              LEFT JOIN contact c ON c.id = r.contact_id
              LEFT JOIN company co ON co.id = r.company_id
             WHERE r.status = 'em_campo'
               AND r.previsao_devolucao < current_date
             GROUP BY r.id, c.nome, co.nome""")

        for r in atrasados:
            msg = (f"Olá, {r['responsavel']}. A devolução dos {r['itens']} equipamentos da "
                   f"saída {r['numero']} está em atraso desde "
                   f"{r['previsao_devolucao'].strftime('%d/%m')} ({r['dias']} dia(s)). "
                   f"Precisamos combinar a devolução ainda hoje — o atraso gera diária "
                   f"adicional conforme o termo assinado.")
            titulo = (f"⚠ Atraso de {r['dias']} dia(s) — {r['responsavel']} ({r['numero']}) · "
                      + f"exposição R$ {float(r['exposicao']):,.0f}".replace(",", "."))
            criados += _pedir_aprovacao(ex, r, "cobranca_atraso", titulo, msg)

        resumo = {"devolve_hoje": len(devolve_hoje), "atrasados": len(atrasados),
                  "aprovacoes_criadas": criados}
        ex.concluir(saida=resumo)
        return resumo
