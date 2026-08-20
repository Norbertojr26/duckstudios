# Identidade

| Caminho | O que é |
|---|---|
| `tokens.css` | cores, tipografia, forma, elevação — importar em todo produto |
| `logo/` | 9 SVGs do logotipo, gerados do `.ai` original |
| `fonts/` | Satoshi — **os arquivos não são versionados**, ver `fonts/README.md` |
| `mock/` | telas de referência em HTML, com tokens e dados reais |

## Logotipo

Gerado por [`../scripts/extrair_logos.py`](../scripts/extrair_logos.py) a partir de `Duck_logo.ai`.
Fundo transparente, texto já em curvas — não dependem da fonte instalada e escalam sem perder.

| Variante | Quando usar |
|---|---|
| `logo-horizontal-{cor,branco,preto}.svg` | topo de tela, cabeçalho de documento |
| `logo-empilhado-{cor,branco,preto}.svg` | espaço estreito, capa, assinatura |
| `marca-{cor,branco,preto}.svg` | favicon, ícone do PWA, avatar |

**cor** sobre fundo claro ou petróleo · **branco** sobre fundo escuro · **preto** em impressão
monocromática.

## Cores da marca

| Token | Hex |
|---|---|
| `--ds-teal` (primária) | `#018682` |
| `--ds-laranja` (acento) | `#F18E25` |
| `--ds-petroleo` | `#082D2A` |

## Telas de referência

`mock/painel.html` e `mock/saida.html` abrem no navegador e usam `tokens.css` de verdade —
são o ponto de partida do código do app, não imagem de apresentação.

Guia de uso e decisões: [`../docs/14-identidade-visual.md`](../docs/14-identidade-visual.md).
