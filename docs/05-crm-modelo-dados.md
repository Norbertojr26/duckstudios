# Modelo de dados do CRM

Schema executável: [`../db/schema.sql`](../db/schema.sql).

## Por que este modelo importa mais que os agentes

Cada tool que um agente vai chamar é uma consulta ou escrita neste banco. Se o modelo estiver errado,
nenhum prompt conserta. Se estiver certo, agentes viram uma camada fina por cima.

## Blocos

```
COMERCIAL          PRODUÇÃO              MÍDIA                LOCAÇÃO           FINANCEIRO
contact            project               media_offload        asset             invoice
company     ─────▶ shoot_day     ◀────── media_file           kit / kit_item    expense
deal               deliverable                                rental
quote              deliverable_version                        rental_line
quote_item                                                    damage_report
price_list                                                    maintenance_log

                       AGENTES (auditoria e controle)
        agent_run · agent_action · approval_request · job_queue · outbox · activity
```

## Decisões que valem explicar

### `rental_line` com constraint de exclusão

```sql
EXCLUDE USING gist (asset_id WITH =, during WITH &&)
    WHERE (status IN ('confirmado','em_campo'))
```

Duas reservas confirmadas do mesmo item com períodos que se sobrepõem são **rejeitadas pelo banco**.
Não é validação de aplicação, não é checagem do agente: é impossibilidade física.

Isso é o que permite dar autonomia de escrita ao agente de rental sem medo. A garantia não depende
de o modelo "lembrar" de checar.

O `hold` fica de fora do bloqueio de propósito: reserva provisória não deve travar venda real.

### Kit não tem disponibilidade

Alugar um kit expande em `rental_line` por `asset`. Se uma lente do kit está em manutenção, o kit
não está disponível — e o sistema sabe *qual* item falta e pode sugerir substituto.

### `media_offload` liga DIT e CRM

É a tabela que responde "cadê o bruto do casamento da Ana?" — pergunta que hoje se responde
abrindo gaveta. Ela também é o checkpoint de retomada do SOP-001.

### `outbox` para tudo que sai

Nenhum SOP chama API externa de forma síncrona. Escreve em `outbox`, um worker entrega quando houver
Starlink. Efeito colateral bom: toda comunicação com cliente fica registrada e revisável, e nada é
enviado sem `aprovado_por` preenchido.

### `agent_run` / `agent_action`

Auditoria completa. Sem isso não existe promoção de autonomia baseada em evidência (a regra das 10
execuções limpas precisa de dados) nem depuração de comportamento.

### `activity` polimórfica

Timeline única por entidade. É de onde o agente de atendimento tira contexto para responder
"o que aconteceu com esse cliente?" sem fazer seis consultas.

## O que ainda falta modelar

- Crew/freelancers e escala de diárias (`crew`, `crew_assignment`, cachê)
- Contratos e direito de imagem/licenciamento (muda preço e prazo de uso)
- Política de retenção e arquivamento de mídia (quando apagar o bruto, e com que autorização)
- Multi-usuário e permissão (só quando entrar mais gente na operação)

Deixados de fora de propósito: entram quando houver uso real, não antes.
