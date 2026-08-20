# Identidade visual

Fontes: arquivo vetorial da marca (`Duck_logo.ai`), pacote **Satoshi** e o catálogo
*Equipamentos para locação · Fevereiro 2026*.
Tokens executáveis em [`../design/tokens.css`](../design/tokens.css) — app, painel, propostas e
termos importam de lá em vez de repetir cor na mão.

---

## Correção: a marca TEM cor

Quando eu só tinha o catálogo, concluí que a identidade era monocromática por decisão. **Estava
errado** — o catálogo usa a versão monocromática do logotipo, mas a marca tem paleta própria, lida
direto dos vetores:

| Token | Hex | O que é |
|---|---|---|
| `--ds-teal` | `#018682` | cabeça do marreco — **cor primária** |
| `--ds-laranja` | `#F18E25` | bico — secundária, acento raro |
| `--ds-petroleo` | `#082D2A` | fundo institucional |
| `--ds-petroleo-esc` | `#0B1E1C` | variação escura |

Isso melhora o produto: o teal vira a **cor de ação** (botão, link, item selecionado) e o app deixa
de ser cinza genérico. O laranja fica para destaque pontual — em área grande ele briga com o teal.

**Nota de contraste:** `#018682` como texto sobre o fundo escuro dá 4,16:1 — reprova em AA para
texto pequeno. Por isso `--ds-acao` é o teal clareado `#2DBDB8` (8,4:1) e o `#018682` fica só como
preenchimento de botão, com texto branco.

## Tipografia: Satoshi

A fonte real da marca é **Satoshi** (Indian Type Foundry, via Fontshare) — variável de 300 a 900.
Substituiu o par Inter/Poppins que eu tinha usado como aproximação.

| Uso | Peso |
|---|---|
| Título de seção | 500 — o catálogo usa título largo e leve, não bold |
| Corpo | 400 |
| Logotipo, botão, número de destaque | 700 |
| Código do item na etiqueta | 900 |

⚠️ **Os arquivos da fonte não estão no repositório.** A licença do Fontshare permite usar em web e
app, mas proíbe redistribuir os arquivos — e commitar num repositório público é redistribuir.
Instruções em [`../design/fonts/README.md`](../design/fonts/README.md).

## Logotipo

Nove SVGs gerados do `.ai` por [`../scripts/extrair_logos.py`](../scripts/extrair_logos.py),
com fundo transparente e texto já em curvas (não dependem da fonte instalada):

| Arquivo | Quando usar |
|---|---|
| `logo-horizontal-cor` · `-branco` · `-preto` | topo de tela, cabeçalho de documento |
| `logo-empilhado-cor` · `-branco` · `-preto` | espaço estreito, capa, assinatura |
| `marca-cor` · `-branco` · `-preto` | favicon, ícone do PWA, avatar |

Regra: **cor** sobre fundo claro ou petróleo · **branco** sobre fundo escuro · **preto/contorno**
em impressão monocromática e fax de contrato.

---

## O que o catálogo define

O sistema visual existe e é coerente. Não precisa criar identidade — precisa **estendê-la para o
produto**.

| Elemento | O que é |
|---|---|
| Fundo | `#161616` — 59% de todos os pixels |
| Superfície | `#272727` — cards, chips, blocos de contato |
| Texto | branco puro e cinza esmaecido |
| Tipografia de título | larga, **peso regular/medium — não bold** |
| Componente recorrente | chip arredondado (`Câmeras · Drones · Iluminação · Gaffer & Grip`) |
| Rodapé | logo pequeno + ano + seção + número de página |

O catálogo usa o logotipo monocromático e nenhuma cor de acento — fundo escuro faz a foto do
equipamento saltar. Faz sentido para catálogo. **Para o produto, não:** um app sem cor de ação
esconde onde se clica. Por isso o produto recupera o teal da marca.

## Cor no produto

Teal = ação. Laranja = acento raro. O resto é estado, e como o fundo é neutro o significado é lido
na hora, sem legenda:

| Cor | Significa |
|---|---|
| verde `#4ADE80` | conferido · disponível |
| âmbar `#FBBF24` | pendente · valor de reposição não confirmado · devolve hoje |
| vermelho `#F87171` | faltando · danificado · atrasado |
| azul `#60A5FA` | em campo |

É exatamente o que a tela de conferência precisa: bipou o item, ele fica verde; sobrou item na
lista, ele fica vermelho. Sem texto, sem leitura, na correria.

## Direção de interface: escuro macio

Referência aprovada: superfícies muito escuras, **cantos largos (22–28px)**, cards com sombra
difusa e um fio de luz no topo, hairlines em vez de bordas, tipografia grande e leve.

O que isso vira em token:

| Token | Papel |
|---|---|
| `--ds-elev-1` / `--ds-elev-2` | sombra para baixo **+** `inset` claro no topo. É o par que dá superfície macia — sombra sozinha deixa o card colado no fundo |
| `--ds-elev-afundado` | campo de entrada parece afundado; botão parece elevado. É o que faz "onde eu clico" ser óbvio sem instrução |
| `--ds-grad-surface` | gradiente quase imperceptível no card (topo mais claro). Card chapado em fundo escuro fica sem volume |
| `--ds-r-card: 22px` | canto largo é a assinatura desse estilo. 12px lê como painel de admin |
| `--ds-border` | `rgba(255,255,255,.07)` — hairline, não linha |

Telas de referência construídas com os tokens reais e dados reais do parque:
[`../design/mock/painel.html`](../design/mock/painel.html) e
[`../design/mock/saida.html`](../design/mock/saida.html). Não são imagem: abrem no navegador e são
o ponto de partida do código do app.

## Decisões de aplicação

- **Dark-only.** O catálogo é escuro; o app segue. Tela escura cansa menos em set noturno e não
  estoura a visão de quem acabou de sair de um monitor calibrado.
- **Título em peso regular, não bold.** É o detalhe que separa "parece o catálogo" de "parece
  qualquer app". Os títulos do catálogo são largos e leves.
- **Alvo de toque mínimo de 44px.** O app é usado com pressa, carregando case, no sol. Botão
  pequeno é botão que não funciona em campo.
- **Etiquetas QR são a exceção da regra escura.** Impressão é preto sobre branco: QR invertido
  derruba a leitura de muitos scanners.
- **Desktop primeiro** no painel; a conferência com scan é celular por natureza. Mesmo código,
  layout responsivo — o rail vira barra inferior e a grade de duas colunas vira uma.

## Onde a identidade aparece no produto

| Peça | Uso |
|---|---|
| App de conferência | tokens completos; cor só como estado |
| Termo de responsabilidade | cabeçalho com logo, corpo em preto sobre branco (documento é impresso e assinado) |
| Proposta / orçamento PDF | mesma grade e tipografia do catálogo — proposta e catálogo têm que parecer a mesma empresa |
| Etiquetas QR | preto sobre branco, sem logo (área útil é pequena demais) |
| Painel interno | tokens completos |

## O que ainda falta da marca

- [x] ~~Vetor do logotipo~~ — 9 SVGs em `design/logo/`
- [x] ~~Versão para fundo claro~~ — variantes `-cor` e `-preto`
- [x] ~~Fonte da marca~~ — Satoshi
- [x] ~~Ícone do PWA~~ — `marca-*.svg`
- [ ] Uma variante do logo tem o peito **marrom** em vez de preto (vista no `Arquivo.zip`).
      É alternativa oficial ou versão antiga? Se for oficial, entra como quarta cor.
