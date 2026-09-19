"""Funções — as tags de trabalho de cada equipe (mesa), estilo Maestri.

Cada mesa é uma equipe; cada função é uma capacidade nomeada. O estado é HONESTO:
  * ativa           — pipeline real, funcionando hoje;
  * precisa_conexao — o código está pronto ou planejado, falta a credencial da
                      ferramenta (o requisito diz qual, e a tela Conexões liga);
  * pronta          — credencial conectada, pipeline em implantação (fila do roadmap);
  * fila            — planejada, sem dependência externa, aguardando a vez.

O catálogo embutido (SEMENTE) é decisão de produto e versiona aqui; funções criadas
pelo dono na Sala nascem com origem='dono' e nunca são tocadas pelo semear.
"""
from . import conexoes, db

# (chave, mesa, nome, descricao, requisito, conexao, embutida)
SEMENTE = [
    # Secretária
    ("triagem_email", "secretaria", "Triagem de e-mails",
     "Classifica não lidos sem marcar como lido; lead vira evento para o comercial.",
     "Conexão Gmail", "gmail", True),
    ("rascunho_resposta", "secretaria", "Rascunhos de resposta",
     "Redige respostas curtas; só saem depois do seu OK em Aprovações.",
     "Conexão Gmail", "gmail", True),
    ("agenda_reunioes", "secretaria", "Agenda e reuniões",
     "Datas de diária e reuniões direto na agenda do estúdio.",
     "Conexão Google Agenda", "google_agenda", False),
    ("followup_email", "secretaria", "Follow-up de e-mails",
     "Cobra educadamente e-mail importante sem resposta há X dias (com aprovação).",
     "Nada externo — fila do roadmap", None, False),
    # Comercial
    ("qualificacao_lead", "comercial", "Qualificação de lead",
     "Mensagem vira contato + negócio no funil, com rascunho de resposta A2.",
     "Chave Anthropic", "anthropic", True),
    ("reativacao_rfm", "comercial", "Reativação RFM",
     "Clientes 90+ dias parados viram propostas de contato, um a um no seu OK.",
     "Nada — já roda", None, True),
    ("whatsapp_entrada", "comercial", "WhatsApp de entrada",
     "Lead chegando pelo WhatsApp cai direto na qualificação.",
     "Conexão WhatsApp (Meta Cloud API)", "whatsapp", False),
    ("prospeccao", "comercial", "Prospecção ativa",
     "Lista de alvos por ramo com rascunho de abordagem para você aprovar.",
     "Nada externo — fila do roadmap", None, False),
    ("onboarding_cliente", "comercial", "Onboarding de cliente",
     "Boas-vindas, dados cadastrais e primeiros passos após o negócio fechar.",
     "Nada externo — fila do roadmap", None, False),
    # Propostas
    ("proposta_voz", "propostas", "Proposta por voz",
     "Você dita; nasce proposta com linha do tempo e parciais de aprovação.",
     "Chave Anthropic", "anthropic", True),
    ("minuta_contrato", "propostas", "Minuta de contrato",
     "Proposta aceita gera minuta no template certo, legislação brasileira.",
     "Nada — já roda", None, True),
    ("revisao_juridica", "propostas", "Revisão de cláusulas",
     "Checagem da minuta contra o checklist do audiovisual antes de enviar.",
     "Nada externo — fila do roadmap", None, False),
    # Rental
    ("ronda_devolucoes", "rental", "Ronda de devoluções",
     "Devolve amanhã? Atrasou? Alerta e rascunho de cobrança a cada 15 min.",
     "Nada — já roda", None, True),
    ("anti_overbooking", "rental", "Anti-overbooking",
     "Garantia no banco: o mesmo item nunca sai duas vezes no mesmo período.",
     "Nada — já roda", None, True),
    ("termo_responsabilidade", "rental", "Termo de responsabilidade",
     "Termo assinado na tela na retirada do equipamento.",
     "Nada — já roda", None, True),
    ("manutencao_preventiva", "rental", "Manutenção preventiva",
     "Horas de uso viram lembrete de revisão por item.",
     "Nada externo — fila do roadmap", None, False),
    # DIT / Mídia
    ("offload_verificado", "dit", "Offload verificado",
     "Cópia dupla com hash; formatar cartão só depois do seu OK.",
     "Runtime na máquina (tela Máquinas)", None, True),
    ("etiquetas_qr", "dit", "Etiquetas QR",
     "Etiqueta de patrimônio com QR para conferência rápida.",
     "Nada — já roda", None, True),
    ("inventario_pastas", "dit", "Inventário de pastas",
     "Varre as pastas autorizadas e espelha a estrutura no CRM.",
     "Runtime na máquina (tela Máquinas)", None, True),
    ("proxies", "dit", "Proxies e transcode",
     "Gera proxies leves na máquina para edição remota.",
     "Runtime na máquina — fila do roadmap", None, False),
    # Entrega
    ("vigia_prazos", "entrega", "Vigia de prazos",
     "D-2 e prazo estourado por projeto, todo dia.",
     "Nada — já roda", None, True),
    ("limpeza_drive", "entrega", "Limpeza do Drive",
     "Projeto roxo 15+ dias → limpeza do espelho, só com aprovação, só lixeira.",
     "Runtime na máquina", None, True),
    ("upload_review", "entrega", "Upload de review",
     "Corte aprovado sobe para o cliente ver, com senha.",
     "Conexão Vimeo", "vimeo", False),
    ("assets_cliente", "entrega", "Assets de cliente",
     "Pastas de entrega organizadas e compartilhadas do jeito da casa.",
     "Conexão Google Drive", "google_drive", False),
    ("qa_entrega", "entrega", "QA de entrega",
     "Checklist técnico (áudio, cartela, letreiro) antes de marcar entregue.",
     "Nada externo — fila do roadmap", None, False),
    # Financeiro
    ("faturamento", "financeiro", "Faturamento e NF",
     "Proposta aceita vira fatura; NF emitida no seu OK.",
     "Integração com emissor de NF — fila", None, False),
    ("conciliacao", "financeiro", "Conciliação",
     "Extrato casa com faturas e aluguéis sozinho.",
     "Extrato/Open Finance — fila", None, False),
    ("contas_pagar", "financeiro", "Contas a pagar",
     "Boletos triados pela Secretária entram na régua de vencimento.",
     "Conexão Gmail", "gmail", False),
    # Tráfego
    ("campanhas_meta", "trafego", "Campanhas Meta",
     "Resultados e sugestões de campanha no Instagram/Facebook.",
     "Conexão Meta Ads", "meta_ads", False),
    ("campanhas_google", "trafego", "Campanhas Google",
     "O outro lado do tráfego pago.",
     "Conexão Google Ads", "google_ads", False),
    # Gerente
    ("verificacao_solicitacoes", "gerente", "Verificação de solicitações",
     "Varre a cada hora o que está parado: aprovações antigas, reações com erro.",
     "Nada — já roda", None, True),
    ("cobranca_pendencias", "gerente", "Cobrança de pendências",
     "Proposta sem resposta 7+ dias, tarefa de máquina travada, máquina sumida.",
     "Nada — já roda", None, True),
    ("relatorio_entregas", "gerente", "Relatório de entregas",
     "Resumo semanal do que saiu, do que atrasou e do porquê.",
     "Nada externo — fila do roadmap", None, False),
    # Copywriter (mesa admitida 'copy')
    ("copys_legendas", "copy", "Copys e legendas",
     "Legendas de post e copys curtas no tom da Duck, sob demanda pela delegação.",
     "Chave Anthropic", "anthropic", True),
    ("roteiros_curtos", "copy", "Roteiros curtos",
     "Roteiro de reel/short a partir de um briefing seu.",
     "Chave Anthropic", "anthropic", True),
    ("emails_marketing", "copy", "E-mails de marketing",
     "Texto de e-mail para campanhas; envio só via aprovação.",
     "Chave Anthropic + Gmail", "anthropic", True),
    # Marketing
    ("designer_artes", "marketing", "Designer de artes",
     "Gera artes (posts, thumbs, mockups) a partir de um briefing seu.",
     "Conexão OpenAI (imagens) ou Gemini", "openai_imagens", False),
    ("instagram_organico", "marketing", "Instagram orgânico",
     "Calendário e rascunhos de post; publicar é gesto seu.",
     "Conexão Meta (mesma do WhatsApp/Ads)", "meta_ads", False),
    ("newsletter", "marketing", "Newsletter",
     "Resumo mensal do estúdio para a base de clientes.",
     "Conexão Gmail (envio aprovado)", "gmail", False),
    ("editor_video", "marketing", "Editor de vídeo",
     "Cortes simples de divulgação na máquina do estúdio.",
     "Runtime na máquina — fila do roadmap", None, False),
]


def semear(conn):
    """Catálogo embutido: upsert idempotente. Funções do dono (origem='dono') ficam."""
    for chave, mesa, nome, desc, req, cx, emb in SEMENTE:
        conn.execute("""INSERT INTO funcao (chave, mesa, nome, descricao, requisito,
                                            conexao, embutida, origem)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'catalogo')
                        ON CONFLICT (chave) DO UPDATE
                          SET mesa=EXCLUDED.mesa, nome=EXCLUDED.nome,
                              descricao=EXCLUDED.descricao, requisito=EXCLUDED.requisito,
                              conexao=EXCLUDED.conexao, embutida=EXCLUDED.embutida
                        WHERE funcao.origem = 'catalogo'""",
                     (chave, mesa, nome, desc, req, cx, emb))


def _estado(f):
    tem_cx = bool(f["conexao"])
    ligada = tem_cx and conexoes.conectada(f["conexao"])
    if f["embutida"]:
        return "ativa" if (not tem_cx or ligada) else "precisa_conexao"
    if tem_cx:
        return "pronta" if ligada else "precisa_conexao"
    return "fila"


def listar():
    """Todas as funções com estado calculado agora (credencial pode ter mudado)."""
    out = []
    for f in db.q("SELECT * FROM funcao ORDER BY embutida DESC, nome"):
        out.append({"chave": f["chave"], "mesa": f["mesa"], "nome": f["nome"],
                    "descricao": f["descricao"], "requisito": f["requisito"],
                    "conexao": f["conexao"], "origem": f["origem"],
                    "estado": _estado(f)})
    return out
