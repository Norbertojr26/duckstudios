"""O relógio da casa: uma tarefa asyncio dentro do próprio servidor.

Sem Celery, sem Redis, sem processo extra — menos peças móveis. Desde o modelo de
eventos (docs/20), o relógio não chama agente nenhum: ele só EMITE o evento
`agenda.tique` a cada intervalo e roda o despachante do barramento com frequência —
quem decide quem reage a quê são as ASSINATURAS em barramento.py.
Réplica única no Railway, então não há corrida.
"""
import asyncio
import os
import traceback

INTERVALO = int(os.environ.get("AGENTES_INTERVALO_SEG", "900"))       # tique: 15 min
PASSO = int(os.environ.get("AGENTES_PASSO_SEG", "20"))                # despacho: 20 s
ATIVO = os.environ.get("AGENTES_ATIVOS", "1") not in ("0", "false", "nao")


async def _laco():
    from . import barramento
    await asyncio.sleep(10)                    # deixa o boot terminar antes da primeira passada
    faltam = 0.0
    while True:
        if faltam <= 0:
            barramento.emitir("agenda.tique", "sistema", {})
            faltam = INTERVALO
        try:
            n = await asyncio.to_thread(barramento.despachar)
            if n:
                print(f"[barramento] {n} evento(s) despachados")
        except Exception:                                            # noqa: BLE001
            print("[barramento] passada falhou:\n" + traceback.format_exc())
        await asyncio.sleep(PASSO)
        faltam -= PASSO


def iniciar():
    if not ATIVO:
        print("[agentes] desativados por AGENTES_ATIVOS=0")
        return
    asyncio.get_event_loop().create_task(_laco())
    print(f"[agentes] barramento a cada {PASSO}s · tique de agenda a cada {INTERVALO}s")
