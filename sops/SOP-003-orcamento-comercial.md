---
id: SOP-003
titulo: "Lead → orçamento → follow-up"
versao: 1
dono_humano: ""            # <!-- PREENCHER -->
area: comercial
criticidade: alta
reversibilidade: alta
frequencia: ""             # <!-- PREENCHER: quantos orçamentos/mês? -->
tempo_manual_min: 0
autonomia_alvo: A2
atualizado_em: 2026-01-01
depende_de: []
---

# SOP-003 — Lead, orçamento e follow-up

> **Rascunho.** Este é o SOP que mais depende de você: preço, margem e tom de voz são o seu negócio.
> O agente aqui **nunca** passa de A2 (executa com aprovação) para nada que chegue ao cliente.

## 0. Objetivo e escopo

- **Resultado:** todo lead recebe resposta em < 4h úteis e nenhuma proposta morre por falta de follow-up.
- **No escopo:** captura do lead, qualificação, montagem do orçamento a partir de tabela, follow-up.
- **Fora do escopo:** negociação de preço, desconto, fechamento de contrato — humano.

## 1. Gatilho

| Origem | Gatilho |
|---|---|
| WhatsApp / Instagram / e-mail | mensagem nova de contato não cadastrado |
| Indicação | cadastro manual |
| Recorrente | cliente antigo pedindo novo job |
| Follow-up | proposta enviada há 3 / 7 / 14 dias sem resposta |

<!-- PREENCHER: por onde os leads chegam hoje, em ordem de volume? -->

## 2. Contrato de dados

**Entrada**
```json
{
  "canal": "whatsapp | instagram | email | indicacao | site",
  "mensagem_original": "string",
  "contato": {"nome": "", "telefone": "", "email": ""}
}
```

**Saída**
```json
{
  "deal_id": "uuid",
  "qualificacao": {
    "tipo_servico": "filmagem | edicao | locacao | pacote",
    "data_evento": "date | null",
    "local": "string | null",
    "orcamento_declarado": "number | null",
    "prazo_entrega": "date | null",
    "campos_faltantes": []
  },
  "rascunho_proposta": "path | null",
  "proxima_acao": "string",
  "requer_aprovacao": true
}
```

## 3. Regras de negócio

**Qualificação — os 6 campos mínimos antes de orçar:**

1. Tipo de serviço (filmagem / edição / locação / pacote)
2. Data e duração
3. Local (e se há custo de deslocamento/diária de equipe fora)
4. Entregáveis (quantos vídeos, formatos, durações)
5. Prazo de entrega
6. Quem decide e qual a faixa de orçamento

Faltando qualquer um → agente **pergunta**, não estima.

**Precificação:** o agente monta orçamento **apenas** a partir da tabela cadastrada
(`price_list`). Nunca inventa preço, nunca dá desconto, nunca fecha valor "sob consulta".
Item fora de tabela → escalar.

<!-- PREENCHER: sua tabela de preços — diária de filmagem, hora de edição, diária de cada equipamento,
     deslocamento por km, valor de urgência, política de desconto por volume -->

**Gatilhos de escalonamento imediato ao humano:**
- Valor acima de <!-- PREENCHER: R$ ? -->
- Cliente pede desconto
- Job com direitos de imagem/uso publicitário (licenciamento muda o preço)
- Prazo abaixo do mínimo operacional <!-- PREENCHER: qual? -->

**Pipeline (estágios do funil):**
`novo → qualificado → proposta_enviada → negociacao → ganho | perdido`

Motivo de perda é **obrigatório** — é o dado que melhora a precificação.

## 4. Fluxo

| # | Passo | Tipo | Aut. | Verificação |
|---|---|---|---|---|
| 1 | Criar/localizar contato e empresa no CRM (dedupe por telefone/e-mail) | `[DET]` | A3 | 1 registro, sem duplicata |
| 2 | Extrair da mensagem os 6 campos de qualificação | `[LLM]` | A3 | campos faltantes listados |
| 3 | Redigir pergunta para o que falta | `[LLM]` | **A2** | humano aprova antes de enviar |
| 4 | Checar disponibilidade de agenda e de equipamento na data | `[DET]` | A3 | conflitos listados |
| 5 | Montar orçamento a partir da `price_list` | `[DET]` | A3 | todo item veio da tabela |
| 6 | Gerar PDF da proposta a partir do template | `[DET]` | A3 | PDF gerado |
| 7 | Enviar ao cliente | HUMANO/`[LLM]` | **A2** | nunca envia sem aprovação |
| 8 | Agendar follow-up D+3 / D+7 / D+14 | `[DET]` | A3 | agendado |
| 9 | Redigir follow-up | `[LLM]` | **A2** | aprovado antes de enviar |
| 10 | Registrar desfecho e motivo | `[LLM]` | A3 | estágio atualizado |

## 5. Proibições absolutas

- [ ] **NUNCA** enviar mensagem, proposta ou e-mail ao cliente sem aprovação humana.
- [ ] **NUNCA** conceder desconto, alterar preço ou prometer prazo fora da regra.
- [ ] **NUNCA** confirmar data sem checar agenda e equipamento.
- [ ] **NUNCA** prometer serviço que o studio não presta.
- [ ] **NUNCA** compartilhar dados de outro cliente (nome, valor, material) — nem como referência.
- [ ] **NUNCA** insistir depois de "não" explícito ou pedido de descadastro.

## 6. Definition of Done

- [ ] Contato e deal no CRM, sem duplicata
- [ ] Proposta com todos os itens rastreáveis à tabela de preços
- [ ] Follow-ups agendados
- [ ] Desfecho registrado com motivo

## 7. Idempotência

- Dedupe por telefone normalizado (E.164) + e-mail.
- Mensagem reprocessada não gera segundo deal para o mesmo assunto em janela de 7 dias.
- Follow-up cancelado automaticamente se o cliente responder.

## 8. Observabilidade

Tempo até a primeira resposta · taxa de conversão por canal · ticket médio · motivos de perda ·
propostas sem follow-up (deve ser sempre zero).

## 9. Casos de teste

| # | Cenário | Esperado |
|---|---|---|
| 1 | "quanto custa um vídeo institucional?" | pergunta os 6 campos, não orça |
| 2 | Briefing completo dentro da tabela | rascunho de proposta pronto para aprovação |
| 3 | Data com equipamento já locado | sinaliza conflito antes de propor |
| 4 | Cliente pede 20% de desconto | escala ao humano, não responde sozinho |
| 5 | Mesmo cliente manda 3 mensagens seguidas | 1 deal, não 3 |

<!-- PREENCHER: 3 conversas reais de lead do mês passado, com a resposta que VOCÊ deu (tom de voz) -->
