# 20 · Modelo de eventos — como os agentes trabalham

Decisão do dono (18/09/2026): **todos os agentes trabalham pelo modelo de eventos**
(referência citada: Maestri AI). Nada chama agente diretamente — nem rota, nem outro
agente, nem o relógio.

## O desenho

```
acontece algo ──▶ INSERT em `evento` ──▶ despachante (a cada ~20 s) ──▶ assinantes reagem
   (emitir)          tipo, origem,          barramento.despachar()        auditoria normal
                     payload jsonb                                        (registro.execucao)
```

- **Emitir**: `barramento.emitir(tipo, origem, payload)` — nunca levanta exceção; o
  evento é consequência do trabalho, não pré-condição.
- **Assinar**: entrada na tabela `ASSINATURAS` de `app/agentes/barramento.py`. Código,
  nunca LLM, decide quem reage a quê.
- **Despachar**: o laço em `agenda.py` roda `despachar()` a cada `AGENTES_PASSO_SEG`
  (20 s) e emite `agenda.tique` a cada `AGENTES_INTERVALO_SEG` (15 min). As rotinas
  (ronda do rental, reativação, prazos, triagem do Gmail) são **assinantes do tique**.
- **Registro**: o evento guarda em `reacoes` quem reagiu e com que resultado (ou erro).
  Evento sem assinante não é bug: é registro — aparece no painel "Barramento de
  eventos" da Sala.

## Tipos em uso

| tipo | quem emite | quem assina |
|---|---|---|
| `agenda.tique` | sistema (15 min) | rental, comercial (1×/dia), entrega (1×/dia), secretaria |
| `email.recebido` | secretaria (por e-mail triado) | — (registro) |
| `email.lead_recebido` | secretaria | comercial → qualificar |
| `lead.qualificado` | comercial | — (registro) |
| `proposta.enviada/aceita/recusada` | humano (tela) | aceita → propostas gera minuta |
| `contrato.rascunho_criado` | propostas | — (registro) |
| `aprovacao.concedida/negada` | humano (tela) | — (registro) |
| `maquina.conectada` | sistema (heartbeat novo/reconexão) | — (registro) |
| `tarefa.delegada` | humano (balcão da Sala) | expediente → mesa destino (pipeline nativo ou agente admitido) |
| `agente.admitido` | expediente (roteador) | — (registro; a mesa nasce em `agente_custom`) |

## O que o modelo NÃO muda

- Autonomia: evento não pula aprovação — A2 continua teto para cliente/dinheiro/deleção.
  A reação a `proposta.aceita` cria a minuta em **rascunho** (documento interno);
  quem envia é humano.
- Auditoria: toda reação de agente continua passando por `registro.execucao`.
- Execução de aprovação: aprovar na tela executa na hora (síncrono) e **também** emite
  `aprovacao.concedida` — o evento é registro, não fila de execução.

## Como adicionar um agente/reação

1. Emita o evento onde o fato acontece (`barramento.emitir`).
2. Escreva a reação como função em `barramento.py` (import tardio do agente).
3. Assine: acrescente à `ASSINATURAS`.
4. Novo tipo → linha na tabela acima.
