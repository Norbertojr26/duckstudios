# Hardware em campo: Mac Mini + bateria + Starlink

> Os números abaixo são ordens de grandeza para dimensionamento. **Meça os seus** com um wattímetro
> antes de comprar bateria — consumo real varia com geração de hardware, carga e temperatura.

## 1. Energia — a conta que decide o tamanho da bateria

| Equipamento | Consumo típico | Observação |
|---|---|---|
| Mac Mini (Apple Silicon) | ~5–10 W ocioso · 30–90 W sob carga | transcode e inferência sobem o consumo |
| Starlink (antena padrão) | ~50–75 W médio, picos maiores | costuma consumir **mais que o Mac Mini** |
| Starlink Mini | dezenas de W (bem menor) | vale considerar para locação móvel |
| DAS/RAID 4 baias | ~20–40 W | mais discos, mais consumo |
| Monitor | ~15–30 W | evitável em campo (usar iPad/celular via Tailscale) |

**Regra prática:** some o consumo médio, acrescente 25% de margem, e divida a capacidade útil da
bateria (≈80% da nominal, por conta da eficiência do inversor) por esse total.

Exemplo com números redondos: Mac Mini 40 W + Starlink 60 W + RAID 30 W ≈ 130 W → com margem, 165 W.
Uma estação de 2 kWh entrega ~1,6 kWh úteis → **~10 h** de operação. Para uma diária longa,
2 kWh é o mínimo; 3 kWh dá folga real.

**Requisitos da estação:**
- Inversor **onda senoidal pura** (não modificada).
- Modo UPS / passagem com transferência rápida, para não derrubar a máquina ao trocar de fonte.
- Recarga por carro ou solar se a diária passa do dia.

**Configurar no macOS:** desligar suspensão de disco em ingestão, `caffeinate` durante offload,
e desligamento gracioso por bateria baixa. Perder energia no meio de um offload não corrompe (o SOP
retoma), mas perder no meio de uma escrita no Postgres sem WAL sincronizado, sim.

## 2. Armazenamento — o gargalo real

Estimativa: `GB por hora ≈ Mbps × 0,45`

| Formato | Bitrate aprox. | GB/h |
|---|---|---|
| XAVC-I 4K 24p | ~240 Mbps | ~110 |
| XAVC-I 4K 60p | ~500 Mbps | ~225 |
| ProRes 422 HQ 4K | ~880 Mbps | ~400 |
| RAW compactado (BRAW/R3D, razão média) | 300–1000 Mbps | 135–450 |

**Multiplique por:** nº de câmeras × horas gravadas × **2 destinos** × 1,1 (proxies).

Uma diária de 2 câmeras gravando 4 h em XAVC-I 4K 60p ≈ 1,8 TB de original → **~3,6 TB** com as duas
cópias. O SSD interno do Mac Mini não sustenta isso.

**Configuração mínima recomendada:**

| Papel | Sugestão |
|---|---|
| Sistema + Postgres + proxies | SSD interno do Mac Mini (≥1 TB, idealmente 2 TB) |
| Destino 1 (trabalho) | DAS Thunderbolt em RAID 5/6, NVMe ou HDD conforme orçamento |
| Destino 2 (shuttle) | SSD/HD externo que **viaja separado** do destino 1 |
| Destino 3 (diferido) | nuvem ou HD no studio, sincronizado quando houver banda |

> Destino 1 e destino 2 no mesmo gabinete não são duas cópias — é uma cópia com dois arquivos.
> Queda, roubo ou fogo levam as duas.

**Formatação:** APFS para volumes que ficam no ecossistema Mac; exFAT só para entrega a terceiros
(mais frágil a interrupção). Evitar NTFS via driver de terceiros para mídia crítica.

## 3. Rede

- **Tailscale** em tudo: Mac Mini, seu celular, notebook. Starlink usa CGNAT — não há como abrir
  porta, e você não deveria querer.
- Sincronização para nuvem só com política de banda: em campo, a Starlink é para operação e
  comunicação, não para subir 2 TB.
- O sistema **não pode** depender de rede para nada em campo. Ver "offline-first" em
  [`02-arquitetura.md`](02-arquitetura.md).

## 4. Térmico e físico

- Mac Mini dentro de van/case fechado no calor faz throttling — transcode em fila longa esquenta.
  Garantir ventilação; case rack ventilado é melhor que caixa hermética.
- Fixar cabos Thunderbolt: desconexão durante offload é uma das principais causas de mídia corrompida.
- Etiquetar fisicamente os volumes com o mesmo nome que o SOP usa. Divergência entre etiqueta e
  caminho é fonte constante de erro humano e de agente.

## 5. Checklist de saída para locação

- [ ] Bateria carregada, consumo estimado × horas previstas conferido
- [ ] Destinos 1 e 2 com espaço ≥ 2× a estimativa da diária
- [ ] `pg_dump` da véspera copiado para fora do Mac Mini
- [ ] Modelo local baixado e testado offline (não baixar em campo)
- [ ] Tailscale conectado e testado antes de sair
- [ ] Cartões formatados **na câmera**, com verificação de que o offload anterior está fechado
- [ ] Cabos reserva: Thunderbolt, leitor de cartão, alimentação
