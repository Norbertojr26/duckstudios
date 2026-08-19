---
id: SOP-002
titulo: "Check-out e check-in de locação de equipamento"
versao: 1
dono_humano: ""            # <!-- PREENCHER -->
area: rental
criticidade: alta
reversibilidade: media
frequencia: ""             # <!-- PREENCHER -->
tempo_manual_min: 0        # <!-- PREENCHER -->
autonomia_alvo: A2
atualizado_em: 2026-01-01
depende_de: [SOP-003]
---

# SOP-002 — Check-out e check-in de locação

> **Rascunho.** A parte de conflito de agenda e vistoria já está fechada; valores, prazos e
> política de caução são seus.
>
> **Contexto atual (ago/2026):** o controle é feito de memória e o AssetTiger só registra o retorno —
> a falta aparece na volta, quando já não dá para saber o que saiu. Com outros videomakers usando o
> equipamento na campanha, o check-out passou a ser o passo crítico. Ver
> [`../docs/12-mvp-conferencia-equipamento.md`](../docs/12-mvp-conferencia-equipamento.md).

## 0. Objetivo e escopo

- **Resultado:** equipamento sai e volta com estado documentado, responsabilidade formalizada e
  inventário sempre refletindo a realidade física.
- **No escopo:** reserva, conferência de saída, termo de responsabilidade, vistoria de retorno,
  registro de dano, recolocação em disponibilidade.
- **Fora do escopo:** precificação (SOP-003), cobrança de dano (financeiro), manutenção corretiva.

## 1. Gatilho

| Momento | Gatilho |
|---|---|
| Reserva | orçamento de locação aprovado → cria `hold` de 48h |
| Check-out | dia da retirada, cliente presente |
| Check-in | devolução física |
| Alerta | equipamento não devolvido até `data_fim + 4h` → cobra o cliente |

## 2. Contrato de dados

**Entrada (check-out)**
```json
{
  "rental_id": "uuid — obrigatório",
  "itens": ["asset_id ou kit_id"],
  "operador": "string",
  "fotos": ["path — estado na saída"]
}
```

**Saída**
```json
{
  "status": "sucesso | bloqueado | escalado",
  "itens_conferidos": 0,
  "itens_faltantes": [],
  "termo_path": "string",
  "acao_humana_necessaria": null
}
```

## 3. Pré-requisitos

- Contrato/termo assinado (ou fila de assinatura aberta)
- Cliente cadastrado com documento validado
- Nenhum item com status `manutencao` ou `bloqueado` na lista
- Caução definida <!-- PREENCHER: valor? % do equipamento? só para cliente novo? -->

## 4. Regras de negócio

- **Nem toda saída é aluguel.** Quatro tipos, e o registro precisa distinguir: `locacao_paga`,
  `emprestimo` (amigo do meio), `uso_interno` (job próprio) e `subcontratacao` (videomaker operando
  para você). Sem essa distinção, faturamento por item e taxa de ocupação viram número falso.
  Empréstimo a amigo tem termo simplificado — mas **tem termo**.
- **Anti-overbooking é do banco, não do agente:** a constraint `EXCLUDE USING gist` em
  `rental_line` impede fisicamente duas reservas confirmadas sobrepostas no mesmo `asset_id`.
  O agente **nunca** contorna isso; ele reporta o conflito.
- **Buffer de retorno:** todo item fica indisponível por `+ N horas` após o fim da locação para
  vistoria/limpeza/recarga. <!-- PREENCHER: N = ? (sugestão: 4h) -->
- **Kits:** alugar um kit reserva cada `asset` dentro dele individualmente. Não existe
  "disponibilidade de kit" — existe disponibilidade dos itens.
- **Itens serializados vs. consumíveis:** câmera/lente têm serial e histórico; gel, fita e pilha são
  quantidade. <!-- PREENCHER: o que você controla por serial? -->
- **Cliente novo:** exige aprovação humana no check-out, sempre (A2), independente do valor.

## 5. Fluxo

### Check-out

| # | Passo | Tipo | Aut. | Verificação |
|---|---|---|---|---|
| 1 | Validar reserva: status, período, pendência financeira do cliente | `[DET]` | A3 | sem bloqueio |
| 2 | Gerar checklist de conferência a partir do kit/itens | `[DET]` | A3 | checklist completo |
| 3 | Conferência física item a item (humano marca) | HUMANO | A0 | 100% marcados |
| 4 | Registrar fotos do estado + serial de cada item | `[DET]` | A3 | ≥1 foto por item serializado |
| 5 | Gerar termo de responsabilidade com itens, valores de reposição, período | `[LLM]` | A2 | revisado antes de enviar |
| 6 | Coletar assinatura do cliente | HUMANO | A0 | assinado |
| 7 | Mudar itens para `em_campo`, gravar `checkout_at` | `[DET]` | A3 | inventário atualizado |
| 8 | Agendar lembrete de devolução (D-1 e no dia) | `[DET]` | A3 | agendado |

### Check-in

| # | Passo | Tipo | Aut. | Verificação |
|---|---|---|---|---|
| 9 | Conferência física de retorno contra o mesmo checklist | HUMANO | A0 | 100% conferido |
| 10 | Comparar fotos saída × retorno; sinalizar diferenças visíveis | `[LLM]` | A1 | apenas sugere |
| 11 | Registrar dano/falta → `damage_report` | `[DET]` | A2 | registro criado |
| 12 | Rotina de retorno: baterias, cartões formatados, limpeza de lentes | HUMANO | A0 | checklist |
| 13 | Liberar itens (`disponivel`) após buffer, ou enviar para `manutencao` | `[DET]` | A3 | status coerente |
| 14 | Fechar locação; se houver dano, abrir pendência financeira | `[LLM]` | A2 | revisado |

## 6. Proibições absolutas

- [ ] **NUNCA** confirmar reserva que gere conflito de período.
- [ ] **NUNCA** liberar equipamento sem termo assinado.
- [ ] **NUNCA** marcar item como devolvido sem conferência física humana.
- [ ] **NUNCA** cobrar dano, executar caução ou emitir cobrança automaticamente.
- [ ] **NUNCA** alterar valor de contrato assinado.
- [ ] **NUNCA** marcar item que voltou danificado como `disponivel`.

## 7. Definition of Done

- [ ] Todos os itens com status coerente com a realidade física
- [ ] Termo assinado arquivado e vinculado ao `rental_id`
- [ ] Fotos de saída e retorno arquivadas
- [ ] Danos registrados; itens afetados fora de disponibilidade
- [ ] Locação com `status` final e pendências abertas explicitamente

## 8. Idempotência

- Chave: `rental_id`. Check-out repetido é no-op se `checkout_at` já existe.
- Queda no meio da conferência: checklist é persistido item a item, retoma de onde parou.
- **Offline:** check-out e check-in funcionam 100% offline; assinatura e envio sincronizam depois.

## 9. Exceções

| Condição | Ação | Bloqueia? |
|---|---|---|
| Item indisponível na hora | sugerir substituto equivalente, exigir aprovação humana | sim |
| Cliente com pendência financeira | bloquear e escalar ao dono | sim |
| Devolução atrasada > 4h | notificar cliente e operador, calcular diária extra (não cobrar) | não |
| Dano relevante | fotografar, registrar, escalar; não estimar valor sozinho | sim (liberação) |
| Item não devolvido | manter `em_campo`, escalar imediatamente | sim |

## 10. Observabilidade

- Taxa de ocupação por item (base para decidir compra de equipamento)
- Receita por item / valor de aquisição (payback real)
- Danos por cliente e por item
- Atrasos de devolução por cliente

## 11. Casos de teste

| # | Cenário | Esperado |
|---|---|---|
| 1 | Reserva simples sem conflito | confirmada |
| 2 | Reserva sobreposta a locação confirmada | rejeitada pelo banco, agente reporta conflito |
| 3 | Devolução com lente riscada | dano registrado, item para `manutencao`, não liberado |
| 4 | Devolução 1 dia atrasada | diária extra calculada, notificação, sem cobrança automática |

<!-- PREENCHER: 3 locações reais recentes como golden runs -->
