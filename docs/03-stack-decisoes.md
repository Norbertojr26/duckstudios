# Stack e decisões

Cada decisão vem com o motivo e o que foi **descartado** — se o contexto mudar, você sabe o que
reconsiderar.

## Quadro final

| Camada | Escolha | Descartado | Motivo |
|---|---|---|---|
| Banco | **PostgreSQL 16** (Docker) | SQLite | precisa de `tstzrange` + `EXCLUDE USING gist` para impedir overbooking no nível do banco |
| API / tools | **Python 3.12 + FastAPI** | — | ecossistema de mídia e IA é Python |
| Fila | **Postgres `SKIP LOCKED`** ou `arq` | Celery + Redis | menos peças móveis em máquina única com energia instável |
| Interface do CRM (Fase 1) | **NocoDB/Django-admin sobre o Postgres** | UI custom já na Fase 1 | UI usável em dias, não meses; UI custom depois que o modelo estabilizar |
| Loop de agente | **Claude Agent SDK** ou loop próprio (~200 linhas) | CrewAI | CrewAI otimiza conversa entre agentes; seu gargalo é confiabilidade de tool, não conversa |
| Orquestração | **máquina de estados no Postgres**; LangGraph só se ficar complexo | LangGraph na Fase 1 | não adicionar framework antes de existir problema que ele resolva |
| Tools | **MCP servers próprios** | tools embutidas no framework | MCP desacopla: troca de modelo/framework não reescreve as tools |
| Inferência local | **Ollama** (simples) ou **MLX** (mais rápido no Apple Silicon) | LM Studio | Ollama tem API estável e roda headless; MLX quando quiser performance |
| Modelo local | Hermes 3 / Qwen / Llama 8B para tarefas fechadas | 8B para decisão crítica | function calling de 8B ainda erra; usar com JSON Schema + retry |
| Modelo de fronteira | API para redação e raciocínio | depender só de local | qualidade onde o texto chega no cliente |
| Mídia | `ffmpeg`, `exiftool`, `mediainfo`, `rsync`, **`ascmhl`**, `xxhsum` | md5 solto | MHL é padrão de indústria e interoperável |
| Offload (Fase 1) | **Hedge ou ShotPut Pro** | offload caseiro já na Fase 1 | não reescrever software crítico de mídia antes da hora |
| Interface de chat | **Telegram bot** | Chainlit como principal | Telegram já está no seu bolso, funciona em campo, dá aprovação com 1 toque |
| Painel | Chainlit ou painel simples | — | ótimo para ver logs, ruim como interface principal em campo |
| Acesso remoto | **Tailscale** | port forward / túnel público | CGNAT do Starlink; e não expor CRM na internet |
| Observabilidade | logs estruturados + **Langfuse local** (opcional) | nada | sem trace você não depura agente |
| Deploy | **Docker Compose** + `launchd` para o que precisa de acesso nativo ao Finder/USB | k8s | é uma máquina |
| Backup do banco | `pg_dump` diário + rclone quando houver banda | — | o banco é o ativo mais difícil de refazer |

## Notas de decisão

### Por que não começar com CrewAI/LangGraph

Frameworks multiagente resolvem **coordenação**. Você ainda não tem o problema de coordenação —
tem o problema de "não existe nenhuma ferramenta confiável para ler e alterar o estado do studio".
Adotar o framework antes cria a ilusão de progresso: agentes trocando mensagens sobre um mundo vazio.

Quando adotar LangGraph: quando houver ≥3 agentes maduros **e** um fluxo real de handoff com estado
compartilhado que a máquina de estados própria já não descreve bem.

### Por que MCP para as tools

Suas tools (consultar disponibilidade, registrar offload, gerar proposta) vão sobreviver a várias
trocas de modelo e framework. Expostas via MCP, elas ficam reutilizáveis por qualquer cliente —
inclusive por você, direto do Claude Code, para operar o studio sem escrever interface.

### Sobre modelo local para function calling

Realidade prática: modelos de 8B rodando quantizados erram nome de parâmetro, inventam campo e
alucinam ID. Mitigações obrigatórias:

1. Saída estruturada com JSON Schema (grammar constraining), não "peça JSON no prompt".
2. Validação + retry (até 2×) e depois escalonamento ao humano.
3. IDs vêm sempre de busca em tool, nunca gerados pelo modelo.
4. Toda escrita relevante passa por aprovação até o SOP provar 10 execuções limpas.

Um Mac Mini M4 Pro com 48–64GB roda modelos bem maiores que 8B — vale testar um MoE (tipo
Qwen3-30B-A3B) que dá qualidade bem superior com velocidade aceitável em Apple Silicon.
Meça tokens/s no seu hardware antes de fixar o modelo.

### Sobre o CRM: construir vs. adotar

CRMs open source (EspoCRM, Twenty) cobrem contato/deal/pipeline bem. Não cobrem o que é específico
seu: **inventário serializado com reserva por intervalo, kits, vistoria de dano e vínculo com mídia
ingerida**. Isso é a parte que dá dinheiro e é a parte que nenhum CRM genérico faz.

Recomendação: **Postgres próprio** com o schema em `db/schema.sql`, e uma UI de administração gerada
(NocoDB apontando para o mesmo banco) na Fase 1. Você tem CRM usável em duas semanas e o schema já
é o que os agentes vão consumir via MCP.
