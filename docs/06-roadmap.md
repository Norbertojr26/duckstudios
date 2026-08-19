# Roadmap

Cada fase tem **critério de saída**. Não começar a próxima sem cumprir.

---

## Fase 0 — Conhecimento (1–2 semanas) · sem código

1. Preencher [`docs/99-perguntas-abertas.md`](99-perguntas-abertas.md).
2. Pontuar tarefas com a matriz de [`sops/README.md`](../sops/README.md).
3. Completar SOP-001 (é a mais crítica e a mais bem definida).
4. Gravar 3 execuções reais de cada SOP → golden runs.
5. Escrever o glossário do studio.

**Saída:** 3 SOPs sem nenhum `<!-- PREENCHER -->`, com 3 casos reais cada.

---

## Fase 1 — Fonte de verdade (3–4 semanas) · **zero agentes**

1. Postgres em Docker no Mac Mini + `db/schema.sql`.
2. Migrar dados reais: clientes, projetos ativos, **inventário completo com valor de reposição**.
3. Cadastrar tabela de preços.
4. UI de administração (NocoDB apontando para o banco) — usar de verdade, todo dia.
5. `pg_dump` diário automatizado.

**Saída:** você opera o studio pelo CRM por 2 semanas sem voltar para a planilha. Se voltar, o
modelo está errado — corrigir antes de seguir.

> Esta é a fase que mais gente pula e é a que decide o projeto.

---

## Fase 2 — Ferramentas determinísticas (2–3 semanas) · ainda sem LLM

1. CLI `duck`: `duck ingest`, `duck rental disponibilidade`, `duck orcamento`, `duck relatorio`.
2. Pipeline de ingestão do SOP-001 completo, com `--dry-run`, retomada e MHL.
   (Na primeira volta, delegar a cópia verificada ao Hedge/ShotPut e automatizar o entorno.)
3. Fila de jobs + worker de outbox.
4. Rodar os golden runs contra a CLI.

**Saída:** um cartão sai da câmera e chega verificado, catalogado e com proxies **com um comando**.
Isso já economiza tempo, mesmo que você pare o projeto aqui.

---

## Fase 3 — Primeiro agente (2–3 semanas)

1. `crm-mcp` **somente leitura**.
2. Bot no Telegram com agente de Atendimento em A1/A3-leitura.
3. Ollama/MLX instalado, tokens/s medidos, roteamento local vs. API definido.
4. `agent_run`/`agent_action` gravando desde a primeira execução.

**Saída:** você pergunta pelo celular "a FX3 tá livre dia 12?" e recebe resposta correta, offline.

---

## Fase 4 — Escrita com aprovação (4–6 semanas)

1. `approval_request` + botões de aprovação no Telegram.
2. Agente DIT aciona o pipeline da Fase 2 (A3 nos passos determinísticos).
3. Agente Rental: check-out/check-in guiados (A2 nas reservas).
4. Agente Comercial: qualificação e rascunho de proposta (A2 sempre).

**Saída:** ≥1 SOP rodando em A3 com 10 execuções consecutivas sem correção.

---

## Fase 5 — Ampliação (contínuo)

1. Agentes Financeiro e Pós.
2. Coordenador — **só agora** faz sentido, e só se houver handoff real.
3. Se a coordenação ficar complexa: avaliar LangGraph.
4. Painel de métricas: tempo economizado, % sem intervenção, erros por SOP.
5. Revisão trimestral de SOPs e níveis de autonomia.

---

## Métricas do projeto

| Métrica | Meta |
|---|---|
| Tempo entre fim da diária e mídia verificada em 2 destinos | < 3h |
| Execuções de SOP sem intervenção humana | > 90% após maturidade |
| Tempo até primeira resposta a lead | < 4h úteis |
| Propostas sem follow-up | 0 |
| Overbooking de equipamento | 0 (garantido pelo banco) |
| Perda de material bruto | 0 — **inegociável** |

## Anti-metas

Sinais de que o projeto saiu do trilho:

- Mais de 2 agentes antes da Fase 4.
- Framework multiagente instalado antes do CRM estar em uso diário.
- Qualquer automação de escrita/apagamento na origem da mídia.
- Agente enviando mensagem a cliente sem aprovação.
- SOP sem golden run.
