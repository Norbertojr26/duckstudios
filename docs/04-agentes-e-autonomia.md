# Agentes e níveis de autonomia

## Escala de autonomia

| Nível | Nome | O agente... | Usar quando |
|---|---|---|---|
| **A0** | Proibido | não toca — só humano | irreversível: formatar cartão, pagar, assinar |
| **A1** | Observa e sugere | analisa e propõe; humano executa | processo novo, ou julgamento subjetivo |
| **A2** | Executa com aprovação | prepara a ação; humano aprova com 1 toque | tudo que chega ao cliente ou mexe em dinheiro |
| **A3** | Executa e reporta | age e informa depois | reversível, verificável, com 10 execuções limpas |
| **A4** | Autônomo | age e só reporta em agregado | tarefa madura, baixo risco, alto volume |

**Regra de promoção:** 10 execuções consecutivas sem correção humana → sobe um nível.
**Regra de rebaixamento:** 1 erro que precisou de correção → desce um nível, e o motivo entra no
histórico do SOP. Sem exceção — é o que mantém a confiança calibrada.

**Regra de teto:** nada que envie mensagem a cliente, mexa em dinheiro ou apague dado passa de A2.
Isso não muda com o tempo nem com maturidade.

## Papéis

Comece com **um**. Os outros existem no papel para você saber onde a coisa vai dar.

### 1. Atendimento / Secretária — *o primeiro a construir*

- **Faz:** responde "qual a agenda de setembro?", "a FX3 está livre dia 12?", "quanto faturamos com
  locação esse mês?", "cadê o bruto do casamento da Ana?"; agenda; lembra prazos.
- **Autonomia:** A3 para leitura, A2 para qualquer coisa que saia da máquina.
- **Por que primeiro:** é read-only. Você ganha confiança no sistema sem risco, e ele obriga o CRM a
  estar correto.

### 2. DIT / Mídia

- **Faz:** SOP-001 (ingestão), proxies, organização, catalogação, relatório de diária.
- **Autonomia:** A3 nos passos determinísticos, **A0 para qualquer escrita na origem**.
- **Nota:** 95% desse agente é script. O LLM só entende o pedido e escreve o relatório.

### 3. Rental / Inventário

- **Faz:** SOP-002; disponibilidade; lembretes de devolução; alerta de manutenção; relatório de
  ocupação e payback por item.
- **Autonomia:** A3 para consulta e agendamento, A2 para reserva, A0 para cobrança.

### 4. Comercial

- **Faz:** SOP-003; qualificação; monta orçamento a partir da tabela; follow-up.
- **Autonomia:** **A2 e ponto final** para tudo que o cliente vê.

### 5. Financeiro / ADM

- **Faz:** fechamento de custo de diária, categorização de despesa, conciliação, relatório de
  margem por projeto, lembrete de cobrança.
- **Autonomia:** A3 para relatório e categorização, **A0 para pagar, emitir NF ou cobrar**.

### 6. Pós / Edição

- **Faz:** monta estrutura de projeto no NLE, importa proxies, gera versões de entrega
  (16:9/9:16/1:1), sobe para review, controla versionamento e aprovação.
- **Autonomia:** A3 para preparo, A2 para enviar ao cliente.
- **Nota:** "montar o vídeo" **não** é tarefa de agente. Preparar tudo para você montar é — e é onde
  está a hora de trabalho que dá para recuperar.

### 7. Coordenador — *o último a construir*

- **Faz:** recebe pedido amplo, decide qual SOP/agente aciona, acompanha, junta o resultado.
- **Quando:** só depois de ≥3 agentes maduros. Antes disso, o coordenador é você.

## Ordem de construção

```
Atendimento (read-only)  →  DIT  →  Rental  →  Comercial  →  Financeiro  →  Pós  →  Coordenador
       Fase 2               Fase 3   Fase 3      Fase 4        Fase 4       Fase 5    Fase 5
```

## Interface de operação

- **Telegram** como canal principal: funciona no celular, em campo, com Starlink instável; aprovação
  A2 é um botão inline (`✅ Aprovar` / `✏️ Ajustar` / `❌ Cancelar`).
- **CLI `duck`** para tudo: qualquer coisa que o agente faz, você consegue fazer digitando.
- **Painel local** para logs, fila e histórico de execuções.

## Auditoria (não negociável)

Toda execução grava:

```
agent_run:    trace_id · agente · sop_id · gatilho · início/fim · status · custo
agent_action: cada tool call, argumentos, resultado, quem aprovou, quando
```

Sem isso você não consegue responder "por que o agente mandou essa proposta para esse cliente?" —
e um dia essa pergunta vai aparecer.
