# Arquitetura

## Princípio 1 — Determinístico por padrão, LLM na borda

```
        ┌──────────────── BORDA (LLM) ───────────────┐
entrada │ interpretar pedido em linguagem natural    │
humana →│ resolver ambiguidade · escolher qual SOP   │→ chamada de tool
        └────────────────────────────────────────────┘
                              ↓
        ┌──────────── NÚCLEO (100% código) ──────────┐
        │ copiar · hashear · consultar · calcular    │  ← LLM nunca entra aqui
        │ gravar no banco · gerar PDF · rodar ffmpeg │
        └────────────────────────────────────────────┘
                              ↓
        ┌──────────────── BORDA (LLM) ───────────────┐
        │ redigir relatório · decidir se escala      │→ humano
        └────────────────────────────────────────────┘
```

Toda tool é um comando de CLI que **funciona sem LLM nenhum**. O agente é uma interface conveniente
para chamá-la — não uma dependência. Se o modelo local sair do ar em locação, você digita o comando.

## Princípio 2 — O CRM é a memória

Não existe "estado do agente" fora do Postgres. Conversas, decisões, execuções, aprovações — tudo
em tabela. Consequências:

- Reboot no meio de uma tarefa não perde nada.
- Você consegue auditar *por que* o agente fez algo, meses depois.
- Trocar de framework de agente não perde histórico.

## Princípio 3 — Offline-first, não offline-fallback

A Starlink cai. Em locação, cai mais. O sistema é projetado assumindo **sem internet como estado
normal**:

| Camada | Sem internet |
|---|---|
| Ingestão de mídia | funciona 100% — nunca depende de rede |
| CRM (leitura/escrita local) | funciona 100% |
| Check-in/check-out de rental | funciona 100% |
| LLM local (Ollama/MLX) | funciona |
| LLM de fronteira (API) | indisponível → degrada para modelo local ou enfileira |
| Envio ao cliente / e-mail / NF | enfileira, envia quando voltar |

Padrão: **outbox**. Toda ação que sai da máquina vira linha numa tabela `outbox` com `status`,
entregue por um worker quando houver rede. Nada de chamada síncrona a serviço externo dentro de um SOP.

## Diagrama de componentes

```
┌───────────────────────────── Mac Mini (Docker Compose) ─────────────────────────────┐
│                                                                                      │
│  Telegram / WhatsApp ──┐                                                             │
│  Painel web local ─────┼──▶  API (FastAPI)                                           │
│  CLI `duck ...`  ──────┘         │                                                   │
│                                  ├──▶ Loop de agente ──▶ MCP servers                 │
│                                  │      (modelo)          ├── crm-mcp    (Postgres)  │
│                                  │                        ├── media-mcp  (ffmpeg…)   │
│                                  │                        ├── rental-mcp             │
│                                  │                        └── fin-mcp                │
│                                  │                                                   │
│                                  ├──▶ Fila de jobs (Postgres SKIP LOCKED)            │
│                                  │      └── workers: ingest, proxy, outbox, lembrete │
│                                  │                                                   │
│                                  └──▶ PostgreSQL 16  ◀── fonte de verdade            │
│                                                                                      │
│  Inferência local: Ollama / MLX  ────────────────┐                                   │
│  Inferência remota: API (via Starlink)  ─────────┘ roteamento por tarefa + rede      │
└──────────────────────────────────────────────────────────────────────────────────────┘
        │                              │                          │
   DAS/RAID (mídia)            Tailscale (acesso remoto)     Nuvem (backup diferido)
```

## Roteamento de modelo

Não existe "um modelo". Existe uma política:

| Tarefa | Modelo | Por quê |
|---|---|---|
| Classificar mensagem, extrair campos, decidir SOP | local 8B | barato, rápido, offline, tarefa fechada |
| Redigir proposta comercial / e-mail a cliente | fronteira (API) | qualidade de texto importa e passa por aprovação |
| Analisar contrato, planejar tarefa multi-etapa | fronteira | raciocínio |
| Qualquer coisa em campo sem rede | local | é o que tem |

Toda saída de LLM que alimenta código passa por **JSON Schema + validação**. Modelo local de 8B
erra formato com frequência não desprezível; a validação com retry é obrigatória, não opcional.

## Segurança e permissão

- Cada MCP server expõe tools com permissão explícita: `read`, `write`, `write_com_aprovacao`.
- Toda tool de escrita registra em `agent_action` antes e depois.
- Ações que tocam cliente ou dinheiro passam por `approval_request` — o agente cria, humano aprova
  no Telegram/painel, worker executa.
- Acesso remoto **só** por Tailscale. Nenhuma porta exposta na internet, ainda mais numa máquina
  atrás de Starlink com CGNAT.
- Dados de cliente (contrato, documento, direito de imagem) são LGPD: não saem da máquina sem
  necessidade, e o que vai para API de LLM deve ser minimizado.
