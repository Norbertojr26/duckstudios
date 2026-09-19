"""Conexões com ferramentas externas — Gmail, Anthropic, WhatsApp, Slack etc.

As credenciais moram na tabela `conexao` (config jsonb) para o dono conectar tudo pela
tela Dados → Conexões, sem tocar no Railway. As variáveis de ambiente continuam valendo
como fallback: um deploy antigo com GMAIL_USUARIO no serviço segue funcionando igual.

Segredo nunca volta para o navegador: a tela só recebe QUAIS campos estão preenchidos.
"""
import json
import os

from . import db

# O catálogo é a fonte da tela. "estado" ativo = já existe agente usando; "fila" = o campo
# guarda a credencial mas a integração ainda vai chegar (fila viva do docs/06-roadmap).
CATALOGO = [
    {"chave": "gmail", "nome": "Gmail", "agente": "Secretária", "estado": "ativo",
     "descricao": "Triagem da caixa de entrada, leads para o comercial e respostas "
                  "que só saem com a sua aprovação.",
     "ajuda": "Gere uma senha de app: myaccount.google.com → Segurança → Verificação em "
              "duas etapas → Senhas de app → Mail. Cole as 16 letras aqui.",
     "campos": [
         {"chave": "usuario", "rotulo": "E-mail da conta", "tipo": "email",
          "exemplo": "duckcineproducoes@gmail.com"},
         {"chave": "app_senha", "rotulo": "Senha de app (16 letras)", "tipo": "senha",
          "exemplo": "xxxx xxxx xxxx xxxx"}]},
    {"chave": "anthropic", "nome": "Anthropic", "agente": "Todos os agentes",
     "estado": "ativo",
     "descricao": "A chave de IA que os agentes usam para pensar: proposta por voz, "
                  "qualificação de lead, triagem de e-mail.",
     "ajuda": "Crie a chave em console.anthropic.com → API keys.",
     "campos": [
         {"chave": "api_key", "rotulo": "API key", "tipo": "senha",
          "exemplo": "sk-ant-..."}]},
    {"chave": "whatsapp", "nome": "WhatsApp", "agente": "Comercial", "estado": "fila",
     "descricao": "Leads e conversas direto no funil. Primeira da fila de próximas "
                  "features (docs/06).",
     "ajuda": "API oficial (Meta Cloud API): token permanente e ID do número.",
     "campos": [
         {"chave": "token", "rotulo": "Token da Cloud API", "tipo": "senha",
          "exemplo": "EAAG..."},
         {"chave": "numero_id", "rotulo": "ID do número", "tipo": "texto",
          "exemplo": "1055..."}]},
    {"chave": "slack", "nome": "Slack", "agente": "Secretária", "estado": "fila",
     "descricao": "Avisos dos agentes e aprovações sem abrir o CRM.",
     "ajuda": "api.slack.com → Create App → OAuth → Bot User OAuth Token.",
     "campos": [
         {"chave": "bot_token", "rotulo": "Bot token", "tipo": "senha",
          "exemplo": "xoxb-..."}]},
    {"chave": "monday", "nome": "Monday", "agente": "Entrega", "estado": "fila",
     "descricao": "Espelhar projetos e etapas com quem já vive no Monday.",
     "ajuda": "monday.com → avatar → Developers → My access tokens.",
     "campos": [
         {"chave": "api_token", "rotulo": "API token", "tipo": "senha",
          "exemplo": "eyJhb..."}]},
    {"chave": "trello", "nome": "Trello", "agente": "Entrega", "estado": "fila",
     "descricao": "Cartões de projeto sincronizados com o fluxo editorial.",
     "ajuda": "trello.com/power-ups/admin → New → gerar API key e token.",
     "campos": [
         {"chave": "api_key", "rotulo": "API key", "tipo": "senha", "exemplo": ""},
         {"chave": "token", "rotulo": "Token", "tipo": "senha", "exemplo": ""}]},
    {"chave": "meta_ads", "nome": "Meta Ads", "agente": "Tráfego", "estado": "fila",
     "descricao": "Campanhas e resultados para o especialista em tráfego acordar.",
     "ajuda": "business.facebook.com → Configurações → Usuários do sistema → token.",
     "campos": [
         {"chave": "token", "rotulo": "Token de acesso", "tipo": "senha", "exemplo": ""},
         {"chave": "conta_id", "rotulo": "ID da conta de anúncios", "tipo": "texto",
          "exemplo": "act_..."}]},
    {"chave": "google_ads", "nome": "Google Ads", "agente": "Tráfego", "estado": "fila",
     "descricao": "O outro lado do tráfego pago, junto com o Meta.",
     "ajuda": "ads.google.com → Ferramentas → Central de API.",
     "campos": [
         {"chave": "developer_token", "rotulo": "Developer token", "tipo": "senha",
          "exemplo": ""},
         {"chave": "customer_id", "rotulo": "Customer ID", "tipo": "texto",
          "exemplo": "123-456-7890"}]},
    {"chave": "openai_imagens", "nome": "OpenAI (imagens)", "agente": "Marketing",
     "estado": "fila",
     "descricao": "Geração de artes para o designer: posts, thumbs, mockups.",
     "ajuda": "platform.openai.com → API keys. Usada só para gerar imagem.",
     "campos": [
         {"chave": "api_key", "rotulo": "API key", "tipo": "senha", "exemplo": "sk-..."}]},
    {"chave": "gemini", "nome": "Google Gemini", "agente": "Marketing", "estado": "fila",
     "descricao": "Alternativa de geração de imagem para o designer.",
     "ajuda": "aistudio.google.com → Get API key.",
     "campos": [
         {"chave": "api_key", "rotulo": "API key", "tipo": "senha", "exemplo": "AIza..."}]},
    {"chave": "vimeo", "nome": "Vimeo", "agente": "Entrega", "estado": "fila",
     "descricao": "Subir cortes para review e entrega com senha.",
     "ajuda": "developer.vimeo.com → My apps → token com upload.",
     "campos": [
         {"chave": "token", "rotulo": "Access token", "tipo": "senha", "exemplo": ""}]},
    {"chave": "google_drive", "nome": "Google Drive", "agente": "Entrega", "estado": "fila",
     "descricao": "Pastas de entrega e assets de cliente direto do CRM.",
     "ajuda": "console.cloud.google.com → service account com acesso ao Drive do estúdio.",
     "campos": [
         {"chave": "credencial_json", "rotulo": "Credencial (JSON da service account)",
          "tipo": "senha", "exemplo": ""}]},
    {"chave": "google_agenda", "nome": "Google Agenda", "agente": "Secretária",
     "estado": "fila",
     "descricao": "Reuniões e datas de diária na agenda do estúdio.",
     "ajuda": "Mesma service account do Drive, com a agenda compartilhada.",
     "campos": [
         {"chave": "credencial_json", "rotulo": "Credencial (JSON da service account)",
          "tipo": "senha", "exemplo": ""}]},
]

# Fallback: campo do banco → variável de ambiente equivalente (deploys antigos).
_ENV = {("gmail", "usuario"): "GMAIL_USUARIO",
        ("gmail", "app_senha"): "GMAIL_APP_SENHA",
        ("anthropic", "api_key"): "ANTHROPIC_API_KEY"}


def obter(servico):
    try:
        r = db.q1("SELECT config FROM conexao WHERE servico = %s", (servico,))
    except Exception:                                                # noqa: BLE001
        r = None            # banco fora do ar não pode derrubar quem só quer o fallback
    return (r["config"] if r else None) or {}


def salvar(servico, config):
    db.exec_("""INSERT INTO conexao (servico, config) VALUES (%s, %s)
                ON CONFLICT (servico)
                DO UPDATE SET config = EXCLUDED.config, atualizado_em = now()""",
             (servico, json.dumps(config)))


def credencial(servico, chave):
    v = (obter(servico).get(chave) or "").strip()
    if not v:
        v = os.environ.get(_ENV.get((servico, chave), ""), "").strip()
    return v


def gmail():
    """(usuario, senha_de_app) — espaços da senha removidos, como o Google mostra."""
    return credencial("gmail", "usuario"), credencial("gmail", "app_senha").replace(" ", "")


def anthropic_key():
    return credencial("anthropic", "api_key")


def preenchidos(servico):
    """Só os NOMES dos campos com valor (banco ou env) — nunca o valor em si."""
    cat = next((c for c in CATALOGO if c["chave"] == servico), None)
    if not cat:
        return set()
    return {c["chave"] for c in cat["campos"] if credencial(servico, c["chave"])}


def conectada(servico):
    """Todos os campos da conexão preenchidos?"""
    cat = next((c for c in CATALOGO if c["chave"] == servico), None)
    return bool(cat) and len(preenchidos(servico)) == len(cat["campos"])
