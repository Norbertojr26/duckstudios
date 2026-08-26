"""Auditoria de agentes. Toda execução passa por aqui — é o que permite subir autonomia
por evidência (10 execuções limpas) e responder 'por que o agente fez isso?' meses depois."""
import json
import uuid
from contextlib import contextmanager

from .. import db


class Execucao:
    def __init__(self, agente, sop_id, gatilho, entrada=None, modelo=None):
        self.trace_id = str(uuid.uuid4())
        self.sequencia = 0
        r = db.q1("""INSERT INTO agent_run (trace_id, agente, sop_id, gatilho, entrada, modelo)
                     VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                  (self.trace_id, agente, sop_id, gatilho,
                   json.dumps(entrada or {}, ensure_ascii=False, default=str), modelo))
        self.id = r["id"]
        self._concluido = False

    def acao(self, tool, argumentos=None, resultado=None, nivel="A3", erro=None):
        self.sequencia += 1
        db.exec_("""INSERT INTO agent_action (run_id, sequencia, tool, argumentos, resultado,
                                              nivel_autonomia, erro)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                 (self.id, self.sequencia, tool,
                  json.dumps(argumentos or {}, ensure_ascii=False, default=str),
                  json.dumps(resultado or {}, ensure_ascii=False, default=str), nivel, erro))

    def concluir(self, status="sucesso", saida=None, tokens_in=None, tokens_out=None):
        if self._concluido:            # o context manager também conclui; a primeira vale
            return
        self._concluido = True
        db.exec_("""UPDATE agent_run SET status = %s, saida = %s, concluido_em = now(),
                    tokens_entrada = %s, tokens_saida = %s WHERE id = %s""",
                 (status, json.dumps(saida or {}, ensure_ascii=False, default=str),
                  tokens_in, tokens_out, self.id))


@contextmanager
def execucao(agente, sop_id, gatilho, entrada=None, modelo=None):
    ex = Execucao(agente, sop_id, gatilho, entrada, modelo)
    try:
        yield ex
        ex.concluir()
    except Exception as e:                                   # noqa: BLE001
        ex.concluir(status="falha", saida={"erro": f"{type(e).__name__}: {e}"})
        raise
