---
id: SOP-000
titulo: ""
versao: 1
dono_humano: ""            # quem responde por este processo quando dá errado
area: ""                   # dit | pos | comercial | financeiro | rental | adm
criticidade: media         # baixa | media | alta | critica
reversibilidade: alta      # alta | media | baixa | irreversivel
frequencia: ""             # ex: 2x por semana, toda diária, mensal
tempo_manual_min: 0        # quanto tempo custa hoje, feito por humano
autonomia_alvo: A2         # A0..A4 — ver docs/04-agentes-e-autonomia.md
atualizado_em: 2026-01-01
depende_de: []             # ex: [SOP-001]
---

# SOP-000 — [Nome da Tarefa]

## 0. Objetivo e escopo

- **Resultado esperado (em uma frase):**
- **Está no escopo:**
- **NÃO está no escopo:**

## 1. Gatilho (Trigger)

| Tipo | Detalhe |
|---|---|
| Evento | ex: volume montado em `/Volumes/*` com estrutura de câmera reconhecida |
| Comando | ex: `duck ingest --projeto X --camera B` / mensagem no Telegram |
| Agenda | ex: toda segunda 09:00 |

- **Quem pode disparar:**
- **Condições que impedem o disparo:** (ex: já existe execução ativa para este cartão)

## 2. Contrato de dados (I/O)

> Sem isto o SOP não é chamável por outro agente. Preencher sempre.

**Entrada**
```json
{
  "campo": "tipo — descrição — obrigatório?"
}
```

**Saída**
```json
{
  "status": "sucesso | parcial | falha | escalado",
  "trace_id": "uuid",
  "resultado": {},
  "avisos": [],
  "acao_humana_necessaria": null
}
```

**Onde o estado persiste:** (tabela/arquivo — nunca "na memória do agente")

## 3. Pré-requisitos e ferramentas

| Recurso | Verificação antes de iniciar |
|---|---|
| ex: `ffmpeg` | `ffmpeg -version` retorna 0 |
| ex: destino `/Volumes/RAID_A` | montado e com espaço ≥ 2× tamanho da origem |
| ex: banco | conexão OK e SOP não bloqueado |

## 4. Regras de negócio e taxonomia

- **Estrutura de pastas obrigatória:**
- **Padrão de nomenclatura:** (com exemplo real, não abstrato)
- **Glossário:** termos do studio que o agente precisa entender
- **Critérios de triagem/descarte:**

## 5. Fluxo passo a passo

> Marcar cada passo: `[DET]` = determinístico, executado por código; `[LLM]` = exige julgamento.
> Marcar a autonomia do passo: `A0`..`A4`.

| # | Passo | Tipo | Autonomia | Verificação de sucesso |
|---|---|---|---|---|
| 1 | | `[DET]` | A3 | |
| 2 | | `[LLM]` | A2 | |

## 6. Proibições absolutas (lista negativa)

> O agente NUNCA pode, sob nenhuma justificativa:

- [ ] ...
- [ ] ...

## 7. Critério de conclusão (Definition of Done)

Condições **verificáveis por máquina** — nada de "arquivos organizados corretamente":

- [ ] ex: `count(arquivos_destino) == count(arquivos_origem)` para cada destino
- [ ] ex: manifesto MHL gravado e validado em ≥ 2 destinos
- [ ] ex: registro criado no CRM com `status = 'verificado'`

## 8. Idempotência e retomada

- **Rodar duas vezes:** o que acontece? (esperado: no-op ou continuação, nunca duplicação)
- **Cair no meio:** onde está o checkpoint? como retomar?
- **Chave de deduplicação:**

## 9. Exceções e escalonamento

| Condição | Ação automática | Notificar quem | Canal | Bloqueia? |
|---|---|---|---|---|
| ex: destino > 90% | pausar | operador | Telegram | sim |
| ex: hash divergente | isolar arquivo, seguir demais | operador + DIT | Telegram | não |

- **Timeout do SOP:** ___ min → escalar
- **Comportamento sem internet:** (deve concluir offline? enfileirar?)

## 10. Observabilidade

- **Logar:** `trace_id`, início/fim, cada tool call, bytes, hashes, decisões do LLM e por quê
- **Onde:** tabela `agent_run` / `agent_action` + arquivo de log da execução junto à mídia
- **Métrica de saúde deste SOP:** (ex: % de execuções sem intervenção humana)

## 11. Casos de teste (golden runs)

> Isto é o que efetivamente "ensina" o agente e detecta regressão. Mínimo 3 casos reais.

| # | Cenário | Entrada | Saída esperada |
|---|---|---|---|
| 1 | caminho feliz | | |
| 2 | borda | | |
| 3 | falha esperada | | |

## 12. Histórico

| Versão | Data | Mudança | Motivo |
|---|---|---|---|
| 1 | | criação | |
