"""Agente Comercial — a qualificação dinâmica do Módulo 2 do SOP.

O LLM faz só o que exige linguagem: classificar o lead (Eventos × Publicidade), extrair os
campos do texto livre e redigir a próxima resposta. Tudo que é regra — porte→equipe, preço,
criação de contato e negócio — é código e tabela.

Autonomia A2 fixa: a resposta ao cliente NUNCA sai daqui. O agente devolve um rascunho e
cria uma aprovação; quem envia é humano. Isso não é fase de amadurecimento — é teto.
"""
import json
import os

from .. import db
from .registro import execucao

AGENTE = "comercial"
MODELO = os.environ.get("AGENTE_COMERCIAL_MODELO", "claude-opus-5")

# Regra de porte → equipe (Módulo 2.3 do SOP), como dado e não como prosa no prompt:
# o modelo lê a tabela, o código valida contra ela, e mudar a regra não mexe em prompt.
PORTES = [
    {"porte": "pequeno", "ate_pessoas": 100,
     "equipe": ["cinegrafista", "fotógrafo"], "profissionais": "1 a 2"},
    {"porte": "médio", "ate_pessoas": 400,
     "equipe": ["2 câmeras", "fotógrafo", "assistente/áudio", "operador de drone"],
     "profissionais": "3 a 5"},
    {"porte": "grande", "ate_pessoas": None,
     "equipe": ["diretor de corte", "operadores dedicados", "DIT local",
                "assistentes de câmera e iluminação"], "profissionais": "6 a 10+"},
]

ESQUEMA = {
    "type": "object",
    "properties": {
        "ramo": {"type": "string", "enum": ["eventos", "publicidade", "locacao", "indefinido"]},
        "campos": {
            "type": "object",
            "properties": {
                "tipo_evento": {"type": ["string", "null"]},
                "publico_estimado": {"type": ["integer", "null"]},
                "local_ambiente": {"type": ["string", "null"]},
                "nivel_cobertura": {"type": ["string", "null"]},
                "data_evento": {"type": ["string", "null"]},
                "duracao_estimada": {"type": ["string", "null"]},
                "investimento_disponivel": {"type": ["number", "null"]},
                "conceito_ideia": {"type": ["string", "null"]},
                "prazo_entrega": {"type": ["string", "null"]},
            },
            "additionalProperties": False,
            "required": ["tipo_evento", "publico_estimado", "local_ambiente",
                         "nivel_cobertura", "data_evento", "duracao_estimada",
                         "investimento_disponivel", "conceito_ideia", "prazo_entrega"],
        },
        "campos_faltantes": {"type": "array", "items": {"type": "string"}},
        "rascunho_resposta": {"type": "string"},
        "observacao_interna": {"type": "string"},
    },
    "required": ["ramo", "campos", "campos_faltantes", "rascunho_resposta",
                 "observacao_interna"],
    "additionalProperties": False,
}

SISTEMA = """Você é o agente de qualificação comercial da Duck Studios, produtora de vídeo e \
locadora de equipamento cinematográfico em Brasília. Você analisa mensagens de leads que chegam \
por WhatsApp/Instagram e produz: a classificação do lead, os campos extraídos, o que ainda falta \
perguntar e um RASCUNHO de resposta — que será revisado por um humano antes de qualquer envio.

Classificação (ramo):
- "eventos": casamento, formatura, corporativo, 15 anos, festival, show — orçamento por escopo \
e dimensionamento de equipe.
- "publicidade": filme publicitário, institucional, branded content, cinema — orçamento pela \
verba disponível do cliente. Filosofia: não cobrar o mínimo para entregar o básico, e sim o \
máximo de qualidade viável dentro da verba. Se a ideia é maior que a verba, proponha um escopo \
realista dentro do valor, sem constranger o cliente.
- "locacao": só aluguel de equipamento.

Regras invioláveis do rascunho:
- NUNCA informe preço, valor ou faixa de valor. Preço sai da tabela do CRM depois, com humano.
- NUNCA confirme data ou disponibilidade — isso depende de agenda que você não vê.
- NUNCA prometa entregável ou prazo específico.
- Pergunte no máximo 3 coisas por mensagem, as mais importantes primeiro.
- Tom: profissional-próximo, direto, brasileiro; sem emoji em excesso (no máximo um), sem \
"prezado", sem parágrafos longos.

Tabela porte→equipe (eventos), para você dimensionar internamente e citar SEM valores:
{portes}
"""


def configurado():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def qualificar(mensagem, nome=None, telefone=None, canal="whatsapp"):
    """Mensagem de lead → contato+deal no CRM, campos extraídos, rascunho aguardando aprovação."""
    with execucao(AGENTE, "SOP-003", f"mensagem:{canal}",
                  {"nome": nome, "telefone": telefone}, modelo=MODELO) as ex:

        if not configurado():
            ex.acao("verificar_configuracao", {}, {"erro": "ANTHROPIC_API_KEY ausente"},
                    erro="sem chave")
            raise RuntimeError(
                "ANTHROPIC_API_KEY não configurada — defina a variável no serviço para "
                "ativar o agente comercial.")

        import anthropic
        client = anthropic.Anthropic()

        # ---- 1. [DET] contato: dedupe por telefone, nunca duplica ----
        contato = None
        if telefone:
            contato = db.q1("SELECT * FROM contact WHERE telefone_e164 = %s", (telefone,))
        if not contato:
            contato = db.q1("""INSERT INTO contact (nome, telefone_e164, origem)
                               VALUES (%s, NULLIF(%s, ''), %s)
                               ON CONFLICT (telefone_e164) DO UPDATE SET nome = contact.nome
                               RETURNING *""",
                            (nome or "Lead sem nome", telefone or "", canal))
        ex.acao("resolver_contato", {"telefone": telefone},
                {"contato_id": contato["id"], "nome": contato["nome"]})

        # ---- 2. [LLM] classificar, extrair, rascunhar ----
        resposta = client.messages.create(
            model=MODELO,
            max_tokens=16000,
            system=SISTEMA.format(portes=json.dumps(PORTES, ensure_ascii=False)),
            output_config={"format": {"type": "json_schema", "schema": ESQUEMA}},
            messages=[{"role": "user", "content":
                       f"Mensagem do lead ({canal}), nome informado: {nome or 'não informado'}:"
                       f"\n\n{mensagem}"}],
        )
        if resposta.stop_reason == "refusal":
            ex.acao("llm_qualificar", {}, {"stop_reason": "refusal"}, erro="refusal")
            raise RuntimeError("o modelo recusou a mensagem — revisar manualmente")
        dados = json.loads(next(b.text for b in resposta.content if b.type == "text"))
        ex.acao("llm_qualificar", {"modelo": MODELO},
                {"ramo": dados["ramo"], "faltantes": dados["campos_faltantes"]})

        # ---- 3. [DET] deal: um por contato por semana, nunca inventa segundo ----
        deal = db.q1("""SELECT * FROM deal WHERE contact_id = %s
                         AND criado_em > now() - interval '7 days'
                         AND estagio NOT IN ('ganho', 'perdido')
                        ORDER BY criado_em DESC LIMIT 1""", (contato["id"],))
        if not deal:
            titulo = {
                "eventos": f"Evento — {dados['campos'].get('tipo_evento') or 'a definir'}",
                "publicidade": "Publicidade — qualificação",
                "locacao": "Locação de equipamento",
            }.get(dados["ramo"], "Lead — qualificação")
            deal = db.q1("""INSERT INTO deal (contact_id, titulo, tipo_servico, estagio,
                                              valor_estimado)
                            VALUES (%s, %s, %s, 'novo', %s) RETURNING *""",
                         (contato["id"], titulo,
                          "locacao" if dados["ramo"] == "locacao" else
                          "filmagem" if dados["ramo"] == "eventos" else "pacote",
                          dados["campos"].get("investimento_disponivel")))
        ex.acao("resolver_deal", {}, {"deal_id": deal["id"], "titulo": deal["titulo"]})

        # ---- 4. [DET] registrar a conversa e pedir aprovação do rascunho (A2) ----
        db.exec_("""INSERT INTO activity (entidade_tipo, entidade_id, tipo, conteudo, autor)
                    VALUES ('deal', %s, 'mensagem', %s, %s)""",
                 (deal["id"], f"[lead via {canal}] {mensagem}", "cliente"))
        db.exec_("""INSERT INTO approval_request (run_id, titulo, descricao, payload)
                    VALUES (%s, %s, %s, %s)""",
                 (ex.id,
                  f"Responder lead — {contato['nome']} ({dados['ramo']})",
                  dados["rascunho_resposta"],
                  json.dumps({"acao": "enviar_mensagem", "deal_id": str(deal["id"]),
                              "canal": canal, "corpo": dados["rascunho_resposta"],
                              "observacao_interna": dados["observacao_interna"]},
                             ensure_ascii=False)))
        ex.acao("pedir_aprovacao", {"deal": str(deal["id"])},
                {"rascunho_chars": len(dados["rascunho_resposta"])}, nivel="A2")

        uso = resposta.usage
        ex.concluir(saida={"ramo": dados["ramo"], "deal_id": str(deal["id"])},
                    tokens_in=uso.input_tokens, tokens_out=uso.output_tokens)
        return {"ok": True, "ramo": dados["ramo"], "deal_id": str(deal["id"]),
                "campos": dados["campos"], "campos_faltantes": dados["campos_faltantes"],
                "rascunho_aguardando_aprovacao": dados["rascunho_resposta"]}
