# Necessidades organizadas e priorizadas

Base: [`10-como-funciona-hoje.md`](10-como-funciona-hoje.md).

---

## Separação que precisa ser feita antes de qualquer coisa

Você trouxe cinco assuntos misturados. Eles não têm o mesmo prazo, nem o mesmo tipo de solução:

| # | Necessidade | Natureza | Resolve com |
|---|---|---|---|
| 1 | Conferir equipamento na saída e na volta | **operacional, urgente** | software pequeno |
| 2 | Controlar patrimônio e locação | operacional | software médio |
| 3 | Não perder lead / responder e dar follow-up | comercial | processo + software |
| 4 | **Achar cliente grande** | **estratégico** | posicionamento e prova — *não é software* |
| 5 | Agentes automatizando tarefas repetitivas | infraestrutura | vem depois de 1–3 |

O item 4 é o que você declarou como maior problema. É também o único que **nenhum sistema resolve
sozinho**. Vale ser direto sobre isso antes de gastar meses construindo a coisa errada.

---

## P0 — Agora: conferência de equipamento (2–3 semanas)

**Por quê primeiro:** é a única necessidade que você mesmo classificou como *vital*, tem prazo
(a campanha está rodando), tem escopo pequeno e fechado, e o risco de não fazer é perda de patrimônio.

**O gap é preciso e pequeno:** o AssetTiger tem check-in, não tem check-out. Você não precisa de um
CRM inteiro para tapar isso — precisa de uma tela de saída com scanner.

**Situação de risco atual:** o controle é sua memória, e agora **outros videomakers estão com o
equipamento**. Sua memória funcionou porque você era o único operador. Esse pressuposto acabou.
"Não sumiu nada até hoje" descreve o passado, não o risco de agora.

Spec completa em [`12-mvp-conferencia-equipamento.md`](12-mvp-conferencia-equipamento.md).

---

## P1 — Curto prazo: patrimônio + locação como sistema (4–6 semanas)

Extensão natural do P0, usando o mesmo banco:

- Inventário completo com valor de reposição (base do termo de responsabilidade)
- Distinção entre **locação paga · empréstimo · uso interno · subcontratação**
  (sem isso, faturamento por item e taxa de ocupação são números falsos)
- Reserva por período com **overbooking impossível no banco** (já implementado em `db/schema.sql`)
- Termo de responsabilidade gerado e assinado no celular
- Manutenção, dano, e payback por item

**Decisão a tomar:** migrar do AssetTiger ou conviver? Recomendação: exportar o CSV dele como carga
inicial e migrar de vez. Manter dois inventários é garantia de que os dois ficam errados.

---

## P2 — Comercial: o problema é conversão, não só prospecção

Aqui preciso confrontar sua leitura com seus próprios números.

Você disse: *"o que eu não consigo é achar esses clientes."*
Seus dados: ⚠️ **70+ leads respondidos, 1 fechamento.**

Isso não é escassez de lead — é **1,4% de conversão**. Com R$ 3.000/ano de assinatura e uma venda,
seu custo de aquisição foi R$ 3.000 para um pacote de R$ 3.800. Descontando freela e produção, essa
venda provavelmente deu prejuízo.

Duas leituras possíveis, e é importante saber qual é a sua:

1. **O segmento está errado.** Noivo em plataforma de casamento compara preço entre 5 fornecedores.
   Não é o cliente que você quer, e você não quer competir nesse jogo.
2. **O processo está furado.** Tempo de resposta, ausência de follow-up, proposta genérica.

Provavelmente é (1) com um pouco de (2). O teste é barato: pegue os últimos 20 leads e meça
**quanto tempo levou até sua primeira resposta** e **quantos receberam um segundo contato**. Se a
resposta demora horas e não há segundo contato, tem conversão a recuperar antes de trocar de canal.

**O que fazer:**
- Instrumentar o funil (é para isso que existem `deal`, `quote` e `activity` no schema)
- Tempo até a primeira resposta < 4h úteis
- Follow-up D+3 / D+7 / D+14 automático — **redigido pelo agente, enviado só com sua aprovação**
- Motivo de perda obrigatório (o banco já força isso)
- Decidir sobre março com dado, não com sensação

---

## P3 — Estratégico: achar cliente de R$ 50k não é problema de software

Esta é a parte em que eu seria um mau conselheiro se prometesse automação.

**Por que e-mail, ligação e visita não deram retorno:** não foi o canal. Nenhuma marca fecha
R$ 80k/mês por causa de uma abordagem fria. Nesse ticket, a decisão exige três coisas que você não
transmite numa mensagem: **prova de que você já fez algo daquele tamanho, risco baixo percebido, e
alguém que responda por você.**

**O que a evidência do seu próprio negócio diz que funciona:** 90% por indicação, e o cliente atual
veio de um colega que delegou o job. Você está tratando isso como acaso. É o seu canal de
distribuição — e é o único que já provou converter.

Quatro movimentos, em ordem de retorno esperado:

**0. Reativação da base (o quick win que o CRM já viabiliza)**
Padrão RFM clássico — recência, frequência, valor: quem já alugou ou fechou job e sumiu há
N meses recebe um contato pessoal. Num case recente de CRM assistido por IA, uma campanha de
reengajamento assim foi a recomendação de maior retorno (R$ 40k). A sua versão: o banco já tem
`rental` e `deal` por cliente — uma consulta lista "clientes sem movimento há 90 dias" e o
agente Rental/Comercial redige o contato (A2, como sempre). Custo quase zero, base quente.

**1. Sistematizar a indicação (maior retorno, menor esforço)**
Hoje ela é passiva. Vira ativa com três coisas: lista nominal de quem já indicou ou poderia indicar;
uma frase clara e específica do que você procura ("produtora que precise de um diretor de fotografia
para retainer semanal de marca" converte, "se souber de algo me avisa" não); e cadência de contato
registrada no CRM. Isso é medível e é onde um agente ajuda de verdade.

**2. Subcontratação por produtoras e agências**
Já aconteceu com você sem esforço. É o caminho mais curto para ticket alto: a agência já vendeu o
retainer, ela precisa de quem produza. Ciclo de venda curto, prova social embutida, e você entra
sem precisar de portfólio de marca própria. Mapear as agências e produtoras da sua região que já
atendem marcas é uma tarefa de pesquisa — isso **um agente faz bem**.

**3. A campanha como prova**
Você está dentro de uma campanha agora. Isso é volume de produção sob pressão, com equipe, e é
exatamente o tipo de caso que credencia para retainer de marca. Trate como case desde já:
material organizado, números (quantas peças, em quanto tempo, com que equipe), depoimento.
Sem isso, em novembro vira só "trabalhei numa campanha".

**4. Uma peça de portfólio do tamanho do que quer vender**
Você quer vender publicidade semanal para marca. Se o portfólio mostra casamento e institucional,
a conversa não começa. Uma peça espontânea, bem produzida, no formato que quer vender, vale mais
que 200 e-mails. É investimento de produção, não de software.

**Onde o agente realmente ajuda no comercial:**

| Ajuda de verdade | Não ajuda |
|---|---|
| Montar e enriquecer lista de contas-alvo | "Achar" cliente de R$ 50k |
| Monitorar sinal de compra (marca lançou produto, abriu vaga de social media, patrocinou evento) | Substituir prova e posicionamento |
| Rascunhar abordagem personalizada por conta | Disparar cold mail em massa |
| **Follow-up disciplinado** — provavelmente seu maior ganho | Negociar preço |
| Preparar briefing antes da reunião | Fechar sozinho |

---

## P4 — Agentes e automação (só depois de P0–P2)

Mantém-se o que está em [`06-roadmap.md`](06-roadmap.md), com uma correção de ordem: o primeiro
agente deixa de ser um "assistente genérico" e passa a ser o que responde **"quem está com o quê,
agora"** e **"esse lead teve follow-up?"** — as duas perguntas que hoje só sua memória responde.

Ingestão de mídia (SOP-001) continua valendo, mas desceu de prioridade: ela dói toda semana, o
equipamento na rua dói uma vez só — e de forma cara.

---

## Quadro-resumo

| Prioridade | Necessidade | Prazo | Tipo |
|---|---|---|---|
| **P0** | App de conferência com scan (saída e volta) | 2–3 semanas | software pequeno |
| **P1** | Patrimônio + locação completo | 4–6 semanas | software médio |
| **P2** | Funil comercial instrumentado + follow-up | paralelo | processo + software |
| **P3** | Posicionamento, indicação sistematizada, case da campanha | contínuo | **negócio** |
| **P4** | Agentes, ingestão de mídia, multiagente | depois | infraestrutura |

## As três decisões que só você toma

1. **Casamento: renova em março ou não?** Depende de conversão até lá — instrumente agora para
   decidir com dado.
2. **Migra do AssetTiger ou convive?** (recomendação: migra)
3. **Qual é o cliente-alvo?** "Marca que precisa de conteúdo recorrente" é largo demais para
   prospectar. Qual setor, qual porte, qual cidade, quem decide? Sem isso, nenhuma lista — feita por
   você ou por agente — vai prestar.
