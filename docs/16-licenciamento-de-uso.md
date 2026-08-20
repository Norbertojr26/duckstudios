# Licenciamento de uso: como começar a cobrar

Você respondeu que **não cobra hoje, mas quer começar**. Este é o documento mais curto do
repositório e provavelmente o de maior retorno por página.

---

## O que é

Produzir um filme e ceder o direito de usá-lo são duas coisas separadas. Quem compra publicidade
está acostumado com isso — agências trabalham assim desde sempre. Quem vende produção sem separar
está entregando uso irrestrito e perpétuo de graça, sem perceber.

Na prática, hoje: você cobra R$ X para produzir uma peça, e o cliente pode rodar aquilo por dez
anos, na TV, em outdoor, em qualquer país. Você já cedeu tudo. E quando ele quiser rodar de novo no
ano que vem, não há nada para renegociar.

## Por que importa justamente para o cliente que você quer

Você quer marca com retainer e ticket alto. Nesse segmento o licenciamento não é firula — é linha
de orçamento esperada. Duas consequências práticas:

1. **Receita recorrente sem produção nova.** A renovação de licença no fim dos 12 meses é uma
   conversa comercial que se repete todo ano, sem set, sem equipe, sem custo variável.
2. **Você passa a parecer quem já trabalha nesse nível.** Um orçamento com linha de cessão de uso
   sinaliza para o cliente que você conhece o jogo dele. Um orçamento sem ela sinaliza o contrário.

## Como está modelado

Três linhas na tabela de preços, todas percentuais sobre o valor de produção:

| Código | O que cobre | % |
|---|---|---|
| `LIC-DIG12` | redes sociais e site, 12 meses | 30% |
| `LIC-TV12` | TV aberta e mídia exterior (OOH), 12 meses | 80% |
| `LIC-PERP` | uso perpétuo e irrestrito | 150% |

Percentual sobre produção, e não valor fixo, porque a licença acompanha o porte da peça: ceder uso
de um filme de R$ 80 mil vale mais que de um de R$ 8 mil.

**São ponto de partida.** Calibre depois das primeiras negociações e ajuste na planilha editável —
aba *Precos_servico*, coluna `valor`.

## Como introduzir sem assustar cliente antigo

O erro é anunciar preço novo. O certo é mudar o **formato da proposta** e deixar o número igual no
começo.

**Passo 1 — separe, mantendo o total.** Onde hoje você escreve "Vídeo institucional — R$ 10.000",
passe a escrever:

```
Produção — 1 filme institucional, 90s                      R$  7.700
Cessão de uso — digital (redes e site), 12 meses            R$  2.300
                                                    Total   R$ 10.000
```

Mesmo preço, mesma proposta aceita. O que mudou é que agora **existe uma linha com prazo**, e daqui
a 12 meses há motivo para conversar.

**Passo 2 — o contrato precisa acompanhar.** A linha na proposta não vale nada se o contrato ceder
direitos sem limite. Precisa dizer: mídia, território, prazo e exclusividade. Sem isso você cobrou
por algo que já tinha dado.

**Passo 3 — cobre de verdade a partir do cliente novo.** Em cliente novo o licenciamento entra como
valor adicional, não fatiado. É onde a receita realmente aparece.

## O que precisa entrar no contrato

| Campo | Exemplo | Por que importa |
|---|---|---|
| Mídia | digital · TV aberta · OOH · cinema · interno | é o que mais muda o preço |
| Território | Brasil · DF · mundial | mercado maior, valor maior |
| Prazo | 12 meses a partir da primeira veiculação | é o que cria a renovação |
| Exclusividade | você pode ou não usar a peça em portfólio | afeta seu próprio material |
| Uso do elenco | direito de imagem tem prazo próprio | **cuidado: costuma ser mais curto que o da peça** |

⚠️ O prazo do direito de imagem do elenco é um risco real e independente do seu. Se você licencia a
peça por 24 meses e o contrato do ator cobre 12, o cliente fica com uma peça que não pode veicular —
e o problema volta para você. Alinhe os dois prazos, sempre.

## Onde isso encosta no sistema

- `price_list` já tem as três linhas `LIC-*`
- `quote_item` aceita item percentual, então a proposta calcula sozinha
- **Falta:** campos de mídia/território/prazo em `contract`, e um alerta de vencimento de licença.
  Entra junto com o módulo de contratos, na Fase 1b.

## Primeiro passo concreto

Na próxima proposta que você mandar, separe as duas linhas mantendo o total. Não muda seu preço,
não muda a conversa, e você já começa a construir o histórico que torna a cobrança normal depois.
