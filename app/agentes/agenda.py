"""Agendador dos agentes: uma tarefa asyncio dentro do próprio servidor.

Sem Celery, sem Redis, sem processo extra — a decisão de arquitetura do projeto é menos
peças móveis. O agente Rental roda em intervalo fixo; os demais são acionados por evento
(mensagem de lead chega via API). Réplica única no Railway, então não há corrida.
"""
import asyncio
import os
import traceback

INTERVALO = int(os.environ.get("AGENTES_INTERVALO_SEG", "900"))       # 15 min
ATIVO = os.environ.get("AGENTES_ATIVOS", "1") not in ("0", "false", "nao")


def _rodou_hoje(agente, gatilho):
    from .. import db
    return db.q1("""SELECT 1 FROM agent_run
                     WHERE agente = %s AND gatilho = %s
                       AND iniciado_em::date = current_date
                       AND status IN ('sucesso', 'em_progresso')""", (agente, gatilho))


async def _laco():
    from . import comercial, entrega, rental
    await asyncio.sleep(10)                    # deixa o boot terminar antes da primeira passada
    while True:
        try:
            resumo = await asyncio.to_thread(rental.rodar)
            if resumo["aprovacoes_criadas"]:
                print(f"[agente rental] {resumo}")
        except Exception:                                            # noqa: BLE001
            print("[agente rental] falhou nesta passada:\n" + traceback.format_exc())

        # diários: rodam na primeira passada do dia, idempotentes por natureza
        for nome, gatilho, fn in (("comercial", "agenda:reativacao", comercial.reativar),
                                  ("entrega", "agenda", entrega.rodar)):
            try:
                if not _rodou_hoje(nome, gatilho):
                    print(f"[agente {nome}] {await asyncio.to_thread(fn)}")
            except Exception:                                        # noqa: BLE001
                print(f"[agente {nome}] falhou:\n" + traceback.format_exc())

        await asyncio.sleep(INTERVALO)


def iniciar():
    if not ATIVO:
        print("[agentes] desativados por AGENTES_ATIVOS=0")
        return
    asyncio.get_event_loop().create_task(_laco())
    print(f"[agentes] rental a cada {INTERVALO}s · reativação e entrega 1×/dia")
