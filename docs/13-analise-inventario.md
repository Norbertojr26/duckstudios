# Análise do inventário e da tabela de aluguel

Fontes: export do AssetTiger (`asset.xlsx`, 156 itens) e planilha `Aluguel de Equipamentos.xlsx`
(abas *Tabela de Aluguel*, *InCine 2026*, *Instruções*), ambas de 20/08/2026.
Carga reproduzível em [`../db/seed_inventario.sql`](../db/seed_inventario.sql), gerada por
[`../scripts/import_inventario.py`](../scripts/import_inventario.py) e validada em PostgreSQL 16.

---

## 1. O tamanho real do problema

| | |
|---|---|
| Itens | **156** |
| Patrimônio (valor de compra) | **R$ 519.110** |
| Diária somada de todo o parque | R$ 15.734 |
| Itens com número de série | **0** |
| Itens com valor de reposição | **0** |
| Itens marcados como "fora" nas planilhas | **0** |

**84% do patrimônio foi comprado nos últimos 20 meses:** R$ 237.610 em 2026 (60 itens) e
R$ 197.440 em 2025 (73 itens). É um parque novo, caro e provavelmente ainda sendo pago.

**Concentração:** top 5 itens = 25% do valor · top 10 = 37% · top 20 = **53%**.
Meia dúzia de itens carrega metade do risco: FX6 (R$ 40k), Storm 1200X (R$ 28k), FX3 (R$ 25k),
Mavic 4 Pro (R$ 22k), FE 28-135 (R$ 14k), RC Pro 2 (R$ 13k), a7 IV (R$ 13k).

> Isto reenquadra a conversa. Não é "controlar umas câmeras" — é **meio milhão de reais em ativo
> controlado por memória**, num momento em que outras pessoas estão operando esse ativo.

## 2. As três planilhas já discordam entre si

O importador comparou as duas fontes item a item e achou **16 divergências**:

| Tipo | Qtd | Exemplo |
|---|---|---|
| Valor de compra diferente | 2 | `0103` Aputure LS 600d Pro: R$ 10.779,61 vs **R$ 15.000** |
| | | `0104` LS 600D V-Mount Charger: R$ 8.000 vs **R$ 6.000** |
| Descrição diferente | 13 | `0093` "Tripé Manfrotto" vs "Tripé" · `0106` "Painel LED NiceFoto" vs "Painel LED" |
| Sem data de aquisição | 1 | `0145` Laowa 12mm T2.9 (R$ 10.000) |

Nenhuma tag sobrando ou faltando — a base é a mesma. O problema é que ela foi copiada e as cópias
começaram a andar separadas. **Em poucos meses, duas fontes de verdade já divergem em R$ 2.220.**
Isso não se resolve com disciplina; resolve-se tendo **uma** fonte.

Na carga, o valor da planilha de aluguel venceu (é ela que gera preço hoje), e as divergências
estão listadas para você decidir. As descrições do AssetTiger foram mantidas por serem mais
específicas — "Tripé Manfrotto" identifica um item, "Tripé" não identifica nenhum dos 17 tripés.

## 3. O problema mais grave: 156 itens, zero números de série

Nenhuma das planilhas traz número de série. Consequências concretas:

- **Seguro.** Apólice de equipamento audiovisual normalmente exige relação com série. Sem isso, ou
  não há cobertura, ou a comprovação de sinistro fica muito mais difícil.
- **Boletim de ocorrência e recuperação.** Câmera sem série registrada é praticamente irrecuperável
  e impossível de provar como sua.
- **Itens idênticos.** Você tem 3 Amaran P60c, 4 Mancety, 3 baterias de Mavic, 7 Solidcom, 6 UWP.
  Sem série, "voltou um P60c" não diz *qual* P60c — e o histórico de dano por item vira ficção.

O AssetTiger tem campo de série; ou ele não foi preenchido, ou não veio na exportação. **Vale
verificar antes de qualquer outra coisa** — se estiver preenchido lá, é só reexportar. Se não
estiver, capturar a série é trabalho que se faz uma vez, junto com a etiquetagem, item por item.

O schema já tem `numero_serie` esperando.

## 4. Valor de compra ≠ valor de reposição

A coluna `Cost` é o que você pagou. O termo de responsabilidade precisa do que custa **repor hoje**.
A diferença não é acadêmica:

- 13 itens são de 2010–2020 (R$ 48.500 de custo histórico). A Pelican 1560 de 2010 a "R$ 5.000"
  não repõe nada pelo preço de 2010.
- Equipamento importado acompanha câmbio: itens de 2025 podem repor bem acima do que custaram.

Se um videomaker perder a FX6 amanhã, o valor no termo é o que você vai conseguir cobrar.
`valor_aquisicao` e `valor_reposicao` são campos separados no schema, e `valor_reposicao` está
**NULL de propósito nos 156 itens** — é uma decisão sua, não um dado a importar. Sugestão: preencher
só nos top 30 itens (que são ~60% do valor) e usar o de compra como piso no resto.

## 5. A regra de precificação que você já tem (e que não está escrita)

A aba *Instruções* diz que o percentual é por categoria. Na prática, não é — e o que você faz
de verdade é **mais correto** do que está documentado. A regra real, decodificada dos dados:

| Faixa | % diária | % semanal | Itens |
|---|---|---|---|
| Câmera principal (e acessório que sai com ela) | 3,5% | 14% | 8 + acessórios |
| Premium (lente, luz grande, monitor, áudio pro, gimbal) | 3% | 12% | ~60 |
| Médio (tripé, bateria, acessório) | 2,5% | 10% | ~70 |
| Case | 2% | 8% | 9 |

Mais uma regra implícita: **acessório herda o percentual do item-mãe.** As baterias do Mavic e do
Avata estão a 3,5% (não 2,5% de "Bateria/Energia") porque saem com o drone. Está certo — só não
está escrito, e é por isso que parece inconsistente.

**Semanal = exatamente 4× a diária** em todas as faixas. É a "semana de 4 diárias", padrão de rental
house. Coerente.

### Exceções que parecem erro de digitação

| Item | Hoje | Esperado pela regra |
|---|---|---|
| `0023` DJI RC PRO 2 (R$ 13.000) | Acessório Geral, 2,5% | sai com o Mavic → 3,5%, como as baterias |
| `0146` Case Laowa 12mm | 3% | 2%, como todos os outros cases |
| `0105` Case Aputure LS 600d | 3% | 2% |
| `0086` Sony 28-70mm | Lente Premium, 2,5% | é lente de kit, não premium — reclassificar |

O `0023` é o mais caro dos quatro: R$ 13.000 cobrando 2,5% enquanto as baterias do mesmo drone
cobram 3,5%.

### Duas lacunas comerciais

1. **Não existe tarifa mensal.** As *Instruções* citam uma aba "Proposta Longa-Metragem" que não veio
   no arquivo. Para longa e para retainer de marca — que é o cliente que você quer — mensal é a
   unidade de negociação, não diária. Padrão de mercado: mês ≈ 3× a semana.
2. **Case cobrado como item separado.** Você fatura a Pelican, o case do Blazar e o case da Aputure
   como linhas próprias. Funciona em planilha; numa proposta, é a linha que o cliente questiona.
   O usual é o case vir embutido no preço do kit. Comercialmente rende mais embutir e mostrar um
   número inteiro.

## 6. Retorno do parque

`dias de locação até o item se pagar = 1 / % diária`

| Faixa | Diárias para pagar o item |
|---|---|
| Câmera principal (3,5%) | 29 |
| Premium (3%) | 34 |
| Médio (2,5%) | 40 |
| Case (2%) | 48 |

Isso é bruto — antes de manutenção, seguro, transporte e ociosidade. Referência de rental house
saudável: um item precisa faturar **25–40% do próprio valor por ano**, o que a 3% significa
**8 a 14 diárias por ano por item**.

Você não sabe se atinge isso, porque não existe registro de saída. É exatamente o dado que o P0
começa a produzir: com 6 meses de histórico, você descobre quais itens se pagam, quais ficam
parados (candidatos a venda) e quais vivem alugados (candidatos a comprar um segundo).

## 7. Kits sugeridos

Os itens já vêm agrupados nos nomes. Formalizar como kit resolve dois problemas de uma vez: a
conferência fica mais rápida e a proposta fica mais limpa.

Totais calculados no banco a partir da carga (não estimados):

| Kit | Itens | Patrimônio | Diária somada |
|---|---|---|---|
| **DJI Mavic 4 Pro** — `0022` + RC Pro 2 `0023` + adaptador `0024` + hub `0025` + baterias `0026`–`0028` | 7 | R$ 45.500 | R$ 1.435,50 |
| **Aputure Storm 1200X** — `0121` + DMX `0123` + Fresnel `0124` + refletor `0122` + cases `0126`,`0127` | 6 | R$ 45.500 | R$ 1.305,00 |
| **Blazar Remus** — `0140`–`0144` (33/50/65/85/125mm) + case `0139` | 6 | R$ 42.000 | R$ 1.240,00 |
| **Aputure LS 600d Pro** — `0103` + charger `0104` + case `0105` | 3 | R$ 23.000 | R$ 690,00 |
| **NiSi Athena Prime** — `0008`–`0010` + adaptadores PL→E `0006`,`0007` | 5 | R$ 22.900 | R$ 677,50 |
| **DJI Avata 2 FPV** — `0013` + goggles `0014` + controles `0015`,`0016` + hub `0017` + baterias `0018`–`0020` + filtros `0021` | 9 | R$ 16.950 | R$ 540,75 |
| **Sony UWP (6 canais)** — `0147`–`0152` | 6 | R$ 15.000 | R$ 450,00 |
| **Hollyland Solidcom SE** — master `0043` + `0044`–`0050` + base `0051` | 9 | R$ 11.100 | R$ 333,00 |
| **Tilta Nucleus-M** — FIZ `0066` + motores `0069`,`0070` + handles `0067`,`0068` + charger `0071` + case `0072` | 7 | R$ 9.100 | R$ 273,00 |
| **Sony UWP-D26** — `0060`–`0062` | 3 | R$ 6.000 | R$ 180,00 |

Os 10 kits cobrem 61 dos 156 itens e **R$ 237.050 — 46% do patrimônio**. Conferir por kit em vez de
item a item é o que faz a saída de 15 itens caber em 2 minutos.

**Regra que o schema já implementa:** kit não tem disponibilidade própria — alugar um kit reserva
cada item individualmente. Se uma lente Blazar está em manutenção, o sistema sabe *qual* falta e
pode sugerir substituto, em vez de simplesmente dizer que o kit não está disponível.

## 8. Cases como contêiner

15 itens foram marcados como `e_container` na carga (Pelican, DeWalt Toughsystem, SKB, cases de
Blazar/Laowa/Aputure/Tilta, case rígido Worldview). Ainda falta dizer **o que mora dentro de cada
um** — isso só você sabe, e é o que permite conferir bipando o case e abrindo a lista do conteúdo.

Preencher isso durante a etiquetagem é o momento certo: você vai ter cada case aberto na mão.

## 9. A proposta InCine 2026

A aba *InCine 2026* é uma seleção de 32 itens — R$ 145.500 de patrimônio, R$ 4.577/dia,
R$ 18.308/semana. Parece uma proposta real montada à mão.

Isso é o SOP-003 na prática: hoje montar essa proposta significa duplicar aba e apagar linhas.
Com o inventário no banco, vira selecionar itens e gerar o PDF — **e o sistema ainda checa se
aqueles itens estão livres nas datas**, o que a planilha nunca vai fazer.

## 10. O que fazer com isso, em ordem

| # | Ação | Quem |
|---|---|---|
| 1 | Conferir se o AssetTiger tem número de série preenchido; se tiver, reexportar | você |
| 2 | Resolver as 2 divergências de valor (`0103`, `0104`) e a data de `0145` | você |
| 3 | Corrigir os 4 percentuais fora da regra (principalmente `0023`) | você |
| 4 | Definir valor de reposição dos ~30 itens de maior valor | você |
| 5 | Imprimir as etiquetas QR e colar (2 por item: corpo e case) | você |
| 6 | Capturar número de série durante a etiquetagem | você |
| 7 | Definir o conteúdo de cada case | você |
| 8 | Criar tarifa mensal e embutir case no preço de kit | você |
| 9 | Subir o banco e rodar a carga | eu |
| 10 | App de conferência (P0) | eu |

Os itens 5, 6 e 7 são **uma única passada física pelo parque**. Vale reservar um dia e fazer os
três juntos, com o celular na mão.
