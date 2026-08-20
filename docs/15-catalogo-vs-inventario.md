# Catálogo × inventário: o que o comercial vende e o patrimônio não conhece

Cruzamento entre o catálogo *Fevereiro 2026* (69 páginas de produto) e os 156 itens do
AssetTiger. Carga dos pendentes em [`../db/seed_03_catalogo.sql`](../db/seed_03_catalogo.sql).

---

## O achado — e a resposta

14 itens do catálogo não existiam no controle patrimonial. **Confirmado: são sublocados de
terceiros.** Isso resolve o mistério e muda como eles são modelados:

- **não entram no patrimônio** — os R$ 518.750 continuam sendo só o que é seu
- **não recebem etiqueta QR nem número de série** — o dono é outro
- **não têm valor de reposição seu** — quem responde pelo dano é o contrato com o fornecedor
- **o preço depende de cotação** — por isso `requer_cotacao = true` e `valor_diaria` fica vazio

Ficam **disponíveis** (você realmente aluga isso hoje), mas marcados para cotar. O agente comercial
lê essa flag e responde *"esse item eu subloco, preciso cotar antes de fechar preço"* em vez de
inventar um valor — que é exatamente o erro que um agente cometeria com o modelo anterior.

**O que ainda falta, e trava o comercial:** de quem você subloca cada um e por quanto.
Sem `custo_diaria` não existe margem; sem `fornecedor_id` não existe a quem ligar. Ambos estão na
aba **Sublocados** da planilha editável, e a view `margem_sublocacao` calcula o resto sozinha.

| Código | Item | Onde | Observação |
|---|---|---|---|
| `CAT-01` | **GoPro 13** | p.11 | Não existe nenhuma GoPro no inventário |
| `CAT-02` | SmallRig Mini Matte Box Lite | p.25 | Inventário só tem a Tilta Mirage (`0073`) |
| `CAT-03` | K&F 82mm Variable Star Filter | p.26 | |
| `CAT-04` | K&F 82mm Variable ND 2-400 | p.26 | |
| `CAT-05` | K&F 67mm Variable ND 2-32 + CPL ¼ | p.26 | |
| `CAT-06` | **Tripé Sirui SQ75A + cabeça S5** | p.39 | Único tripé de vídeo bowl 75mm do catálogo |
| `CAT-07` | **Tilta Hydra** (car mount, ventosas) | p.42 | |
| `CAT-08` | Tilta Shoulder Rig LWS 15mm | p.43 | |
| `CAT-09` | Hollyland M2 | p.62 | Inventário tem Lark Max 1 e 2, não tem M2 |
| `CAT-10` | **Deity TC-SL1 Smart Slate** | p.66 | Inventário tem 3× TC-1, não a claquete |
| `CAT-11` | **Blackmagic ATEM Mini Pro** | p.79 | Switcher de 4 canais para live |
| `CAT-12` | Teleprompter para iPad | p.80 | |
| `CAT-13` | **Baofeng BF-777s — kit 6 rádios** | p.83 | Controlar por quantidade, não por série |
| `CAT-14` | ProAim Bag | p.70 | |

Código `CAT-xx` porque a numeração do AssetTiger é do parque próprio. Se algum deles virar compra,
migra para a sequência numérica e passa a `proprio`.

## `0091` — era cadastro errado, não item faltando

Confirmado: é o **ProAim Breeza** do catálogo (p.41) — 16 rodas Metalon, trilhos, carga de 100 kg,
mala e cabeça SmallRig DH12 inclusa. O cadastro dizia "Jingmei Dolly Slider" a R$ 360.

Corrigido nome, marca e categoria. **O valor ficou vazio de propósito**: os R$ 360 eram de outro
item, e chutar o preço de um Breeza sairia errado nos dois sentidos. Sem valor não há diária —
ela é 3% do valor. Preencher na aba **Itens** da planilha editável.

Efeito no patrimônio: R$ 519.110 → **R$ 518.750** (saiu o R$ 360 que nunca foi desse item).

## Nomes que o catálogo corrige

O catálogo é mais preciso que o cadastro em 11 itens. Já aplicado em
[`../db/seed_02_regras.sql`](../db/seed_02_regras.sql):

| Código | Era | Virou |
|---|---|---|
| `0147`,`0150` | "Sony UWP Receiver" | **Sony UWP-D27 Receptor** |
| `0148`,`0149`,`0151`,`0152` | "Sony UWP Transmitter" | **Sony UWP-D27 Transmissor** |
| `0106`,`0107` | "Painel LED NiceFoto" | NiceFoto 880A Painel LED BiColor |
| `0058` | "Hollyland Lark Max" | Hollyland Lark Max 1 |
| `0090` | "Amaran LightDome Mini SE" | Softbox Amaran Mini 60×60 |
| `0089` | "Softbox Fototudo 120cm" | Softbox Fototudo FT-8120 120×120 |
| `0093` | "Tripé Manfrotto" | Tripé Manfrotto 755XB + cabeça 502AH |
| `0128` | "Jinbei Triple Combo Luva Pino" | Luva-Pino JB300 (combo triplo) |
| `0108` | "C-Stand Girafa" | C-Stand Century Pino |
| `0111`,`0112` | "Tripé Greika" | Tripé Greika WT808 |
| `0099`,`0100` | "Tripé Iconoflash" | Tripé Iconoflash Mini |

O caso dos UWP importa: os 6 itens `0147`–`0152` são na verdade **dois kits Sony UWP-D27**
(cada um = 1 receptor de 2 canais + 2 transmissores), como o catálogo diz na p.58 ("2 unidades").
Cadastrado como seis itens soltos, ninguém consegue alugar "um UWP-D27" — agora existe kit.

## O catálogo é a melhor documentação que você tem

Cada página traz especificação técnica que o cadastro não tem: sensor, montagem, alcance, carga,
CRI, autonomia. Isso alimenta três coisas diretamente:

1. **Descrição de item no app** — o operador vê o que é ao bipar.
2. **Proposta automática** — a linha do orçamento sai com a spec, não só com o nome.
3. **Agente comercial** — quando o cliente pergunta "essa luz dá conta de externa de dia?", a
   resposta está na p.29 (202.500 lux a 1 m), não na sua cabeça.

Vale extrair essas specs para o campo `metadados` do `asset` numa próxima passada. O texto do PDF
já está limpo e estruturado — é trabalho de script, não de digitação.

## Do outro lado: no inventário e fora do catálogo

Normal e esperado, mas vale conferir se algum deveria estar vendendo:

- Todos os cases (Pelican, DeWalt, SKB, Worldview) — são contêineres, não produto
- Sony XLR Handle (`0076`), Vertical Grip a7 III (`0081`), V-Mount Plate (`0083`)
- Baterias V-Mount Rolux (`0078`) e SmallRig VB99 Mini (`0077`)
- Aputure Barn Doors (`0125`), Hyper Reflector (`0129`,`0130`), Bowens Hyper Refletor (`0122`)
- Deity Smart Battery e carregadores (`0133`–`0137`)

Os modificadores da Aputure são os únicos que talvez mereçam página: quem aluga uma Storm 1200X
normalmente quer saber quais acessórios de moldagem vêm junto.
