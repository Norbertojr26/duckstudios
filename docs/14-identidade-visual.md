# Identidade visual

Extraída do catálogo *Equipamentos para locação · Fevereiro 2026* (87 páginas, 1920×1080).
Tokens executáveis em [`../design/tokens.css`](../design/tokens.css) — o app de conferência, o
painel, as propostas e os termos importam de lá em vez de repetir cor na mão.

---

## O que o catálogo já define

O sistema visual existe e é coerente. Não precisa criar identidade — precisa **estendê-la para o
produto**.

| Elemento | O que é |
|---|---|
| Fundo | `#161616` — 59% de todos os pixels do catálogo |
| Superfície | `#272727` — cards, chips, blocos de contato |
| Texto | branco puro e cinza esmaecido |
| **Cor de acento** | **nenhuma** — monocromático integral |
| Tipografia de título | grotesca geométrica, larga, **peso regular/medium — não bold** |
| Tipografia de corpo | neutra, pequena, alto contraste |
| Logotipo | cabeça de marreco (branco, com detalhe do anel do pescoço) + "Duck Studios" em duas linhas, peso alto |
| Componente recorrente | chip arredondado (`Câmeras · Drones · Iluminação · Gaffer & Grip`) |
| Rodapé | logo pequeno + "Duck Studios" + ano + seção + número de página |

**A escolha mais forte é a ausência de cor.** Isso é raro e funciona: fundo escuro faz a foto do
equipamento saltar, e um catálogo de audiovisual que compete pelo olhar do cliente ganha ao não
disputar com o próprio conteúdo.

## Consequência para o app

**Cor no produto só existe como estado.** Como a marca não gasta cor em decoração, quando o app
mostrar verde/âmbar/vermelho o significado é lido na hora — sem legenda:

| Cor | Significa |
|---|---|
| verde `#4ADE80` | conferido · disponível |
| âmbar `#FBBF24` | pendente · valor de reposição não confirmado · devolve hoje |
| vermelho `#F87171` | faltando · danificado · atrasado |
| azul `#60A5FA` | em campo |

É exatamente o que a tela de conferência precisa: bipou o item, ele fica verde; sobrou item na
lista, ele fica vermelho. Sem texto, sem leitura, na correria.

## Decisões de aplicação

- **Dark-only.** O catálogo é escuro; o app segue. Tela escura cansa menos em set noturno e não
  estoura a visão de quem acabou de sair de um monitor calibrado.
- **Título em peso regular, não bold.** É o detalhe que separa "parece o catálogo" de "parece
  qualquer app". Os títulos do catálogo são largos e leves.
- **Alvo de toque mínimo de 44px.** O app é usado com pressa, carregando case, no sol. Botão
  pequeno é botão que não funciona em campo.
- **Etiquetas QR são a exceção da regra escura.** Impressão é preto sobre branco: QR invertido
  derruba a leitura de muitos scanners.
- **Tipografia livre.** Os arquivos do PDF vêm como Type3 (convertidos), então não dá para ler o
  nome real das fontes. `Inter` para interface e `Poppins` para o logotipo chegam perto, são
  gratuitas e resolvem enquanto não houver decisão de licença. **Se você tem os arquivos originais
  da marca, me manda** — troco no `tokens.css` em um minuto.

## Onde a identidade aparece no produto

| Peça | Uso |
|---|---|
| App de conferência | tokens completos; cor só como estado |
| Termo de responsabilidade | cabeçalho com logo, corpo em preto sobre branco (documento é impresso e assinado) |
| Proposta / orçamento PDF | mesma grade e tipografia do catálogo — proposta e catálogo têm que parecer a mesma empresa |
| Etiquetas QR | preto sobre branco, sem logo (área útil é pequena demais) |
| Painel interno | tokens completos |

## O que ainda falta da marca

- [ ] Arquivo vetorial do logotipo (SVG) — hoje só existe rasterizado dentro do PDF
- [ ] Versão do logo para fundo claro (documentos impressos)
- [ ] Nome real das fontes, se houver licença
- [ ] Favicon / ícone do PWA (a cabeça do marreco isolada resolve)
