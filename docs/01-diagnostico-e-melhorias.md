# Diagnóstico da proposta inicial

## Resumo em uma linha

A estrutura que você trouxe é **acima da média** — melhor que 90% do que se vê em projeto de agente.
Os problemas não estão no que tem, estão em **quatro omissões** que só aparecem quando o sistema
encosta em mídia real de cliente.

---

## 1. O que já está certo (não mexer)

- **Começar por SOP, não por código.** Correto. O gargalo de agente autônomo nunca é o modelo, é a
  ausência de processo escrito. Você acertou a ordem.
- **Gatilho explícito.** Muita gente esquece que agente precisa de porta de entrada definida.
- **Definition of Done com verificação de hash.** Isso é pensamento de engenharia, não de "prompt".
- **Fallback com pausa e notificação humana.** Certo — o padrão default deve ser parar, não improvisar.
- **Arquitetura híbrida local + nuvem.** Correta para o cenário de locação.

---

## 2. As quatro omissões que quebram na prática

### 2.1 Falta a marcação **determinístico vs. julgamento**

Este é o erro mais caro do projeto, e ele está escondido no passo "Executar checksum via agente".

> **Regra:** LLM nunca deve *executar* uma cópia, um checksum ou um `rm`. LLM decide **o quê** fazer;
> **código** faz. Se um passo tem resposta única e verificável, ele é script — não é agente.

Na prática isso significa que o SOP-001 inteiro (ingestão de cartão) é um **pipeline determinístico
em Python/shell**. O agente só aparece em duas bordas:

- **Entrada:** interpretar "descarrega o cartão da B do casamento de ontem" → `{projeto: X, camera: B, data: Y}`.
- **Saída:** redigir o relatório e decidir se escala para humano.

Um modelo 8B local errando um argumento de `rsync --delete` custa o material bruto de uma diária.
Nenhum ganho de automação paga isso. Marque cada passo do SOP com `[DET]` ou `[LLM]`.

### 2.2 Falta **nível de autonomia por passo** (e o corolário: lista de proibições)

Seu template trata o SOP como bloco único: ou o agente roda, ou não roda. Na prática, dentro de um
mesmo SOP você quer autonomia diferente por passo — copiar arquivo é A3 (executa e reporta),
apagar cartão é A0 (nunca, só humano).

Adotamos a escala A0–A4 (ver [`04-agentes-e-autonomia.md`](04-agentes-e-autonomia.md)) e, mais
importante, uma **lista negativa explícita** em cada SOP. Lista negativa funciona melhor que lista
positiva porque o modelo não precisa inferir o que não foi autorizado.

Para o seu negócio, as proibições absolutas mínimas são:

- Nunca formatar/apagar cartão de origem — **em hipótese nenhuma**, nem com hash 100% conferido.
  Formatação é ato humano, na câmera, no início da próxima diária.
- Nunca deletar ou sobrescrever arquivo em `RAW/`.
- Nunca enviar e-mail, proposta ou mensagem a cliente sem aprovação humana.
- Nunca emitir nota fiscal, fazer pagamento ou alterar valor de contrato.
- Nunca confirmar reserva de equipamento que gere conflito de agenda sem revisão.

### 2.3 Falta **contrato de dados (I/O) e idempotência**

Seu SOP é prosa. Prosa não compõe. Se o Agente Coordenador precisa chamar o Agente DIT, ele precisa
saber exatamente qual JSON manda e qual JSON recebe. Sem isso, todo handoff entre agentes vira
"telefone sem fio" em linguagem natural — que é onde sistemas multiagente apodrecem.

Além disso, três perguntas que seu template não faz e que decidem se o sistema é usável em campo:

- **O que acontece se rodar duas vezes?** (idempotência)
- **O que acontece se cair na metade?** (retomada — a Starlink *vai* cair, a bateria *vai* acabar)
- **Onde fica o estado?** (no Postgres, não na cabeça do agente nem num JSON solto)

O template v2 tem campos para os três.

### 2.4 Falta **avaliação** — o que separa demo de sistema

Não existe "ensinar o agente" sem casos de teste. O que efetivamente ensina é:

1. Um **glossário** (como você chama as coisas: projeto, diária, kit, cliente).
2. **3 a 5 execuções reais gravadas** por SOP, com entrada e saída esperada ("golden runs").
3. Um **modo dry-run** que imprime o plano sem executar.

Os golden runs viram sua suíte de regressão: trocou o modelo, rodou os 5 casos, comparou. Sem isso
você não tem como saber se uma atualização do Ollama piorou seu agente de ingestão.

---

## 3. Correções técnicas pontuais

### 3.1 MD5/SHA256 → **xxHash64 + manifesto ASC MHL**

MD5 e SHA256 funcionam, mas o padrão da indústria de cinema para offload é **xxHash64** (ordens de
grandeza mais rápido; você está verificando TBs em campo, com bateria contada) e o manifesto
**ASC MHL** (Media Hash List) — formato XML aberto, mantido pela American Society of
Cinematographers, que Silverstack, ShotPut Pro e Hedge leem.

Consequência prática: se você gerar MHL, sua ingestão caseira é **interoperável** com a
pós-produção do cliente e com qualquer casa de finalização. Se gerar `.md5` solto, não é.

> Existe implementação de referência open source (`ascmhl`). Vale usar em vez de escrever o seu.

### 3.2 Você está reescrevendo Hedge/ShotPut — decida conscientemente

Offload verificado com checksum é problema **resolvido** por ferramentas maduras (Hedge, ShotPut Pro,
Silverstack, YoYotta). Escrever o seu significa reencontrar bugs que já custaram material a outras
pessoas: cartões que desmontam no meio, arquivos esparsos, metadados de sidecar (`.XML`, `.THM`,
`.CPI`), estruturas de câmera com clipes segmentados (Sony XAVC spans, Canon CRM, RED `.R3D`
multi-arquivo), nomes duplicados entre cartões.

Duas saídas legítimas:

- **(a) Recomendada para começar:** usar Hedge/ShotPut para a cópia verificada e o agente cuidar de
  tudo **em volta** (nomear, registrar no CRM, gerar proxies, avisar, relatar). Você automatiza 80%
  do trabalho com 20% do risco.
- **(b) Depois:** internalizar a cópia com `ascmhl` + `rsync`, quando os SOPs estiverem estáveis.

### 3.3 3-2-1: uma cópia não é backup

Seu SOP fala em "cópia de segurança" no singular. Regra de set: **mínimo duas cópias em mídias
físicas distintas antes de o cartão sair de circulação**, idealmente três (ex.: RAID de trabalho +
HD shuttle + nuvem quando houver banda). O critério de conclusão do SOP-001 tem que exigir
`N >= 2 destinos verificados`, não `1`.

### 3.4 SQLite → **PostgreSQL**

Seu quadro cita SQLite. Para locação de equipamento isso é uma limitação real: o problema central de
rental é **impedir overbooking** — dois contratos alugando a mesma câmera em períodos que se
sobrepõem. O Postgres resolve isso no banco, com uma linha:

```sql
EXCLUDE USING gist (asset_id WITH =, during WITH &&) WHERE (status IN ('confirmado','em_campo'))
```

Isso torna o overbooking **fisicamente impossível**, mesmo que o agente tenha um bug. É exatamente o
tipo de garantia que você quer quando um LLM tem permissão de escrita. SQLite não tem constraint de
exclusão nem tipo de intervalo. Postgres roda em Docker no Mac Mini sem drama.

### 3.5 Celery é peso morto aqui

Celery + Redis + worker é infraestrutura de web em escala. Numa máquina só, em campo, cada peça a
mais é uma peça a mais que falha quando a bateria oscila. Use uma **fila no próprio Postgres**
(`SELECT ... FOR UPDATE SKIP LOCKED`) ou `arq`/`dramatiq`. Menos partes móveis = mais uptime em locação.

### 3.6 "Openclaw ou Hermes" — são camadas diferentes

Vale desembaralhar, porque isso muda decisão de arquitetura. São **quatro camadas independentes**:

| Camada | O que é | Exemplos |
|---|---|---|
| **Modelo** | os pesos que geram texto | Hermes 3, Llama, Qwen, Claude |
| **Runtime de inferência** | roda o modelo na máquina | Ollama, LM Studio, MLX, llama.cpp |
| **Loop de agente** | dá tools ao modelo e itera | Claude Agent SDK, loop próprio |
| **Orquestração** | estado, filas, delegação, retomada | LangGraph, máquina de estados própria |

**Hermes 3** é modelo (camada 1) — não é framework de agente. Assistentes pessoais open source
(a categoria do "OpenClaw") ocupam as camadas 3–4 e são ótimos para *seu* uso pessoal, mas não são
base de sistema que toca material de cliente: falta auditoria, permissão granular e retomada.

> Não tenho como validar aqui o estado atual/maturidade de um projeto específico chamado "OpenClaw" —
> antes de adotar qualquer um deles, cheque três coisas: **(1)** consegue registrar toda ação em
> banco auditável? **(2)** consegue exigir aprovação humana por ferramenta? **(3)** sobrevive a
> reboot no meio de uma tarefa? Se a resposta a qualquer uma for não, ele serve de interface, não de
> núcleo.

---

## 4. O erro estrutural de sequenciamento

Sua lista de próximos passos começa por "instalar Ollama e testar tool use". Isso é o passo 3, não o 1.

**Multiagente é a última coisa a construir, não a primeira.** A falha clássica é montar seis agentes
com papéis bonitos (secretária, financeiro, comercial) antes de existir **uma** ferramenta confiável
para eles operarem. O resultado é seis agentes conversando entre si sobre um mundo que nenhum deles
consegue ler ou alterar de verdade.

A ordem que funciona:

1. **Fonte de verdade** (Postgres + CRM) — os agentes precisam de um mundo para ler.
2. **Ferramentas determinísticas** (scripts que fazem a tarefa sem LLM nenhum, chamáveis por CLI).
3. **Um** agente, read-only, em A1 (só sugere) — normalmente o de atendimento/consulta.
4. Escrita com aprovação, um SOP por vez, subindo autonomia por evidência.
5. Multiagente **só quando** houver ≥3 agentes maduros que realmente precisem se coordenar.

Cada script da etapa 2 tem valor **independente do agente**: mesmo que você abandone a ideia de
multiagente amanhã, um pipeline de ingestão que roda com um comando já economiza uma hora por diária.

---

## 5. Veredito

| Item | Nota | Ação |
|---|---|---|
| Template de SOP | 7/10 | Usar v2 em [`../sops/_TEMPLATE-SOP.md`](../sops/_TEMPLATE-SOP.md) |
| Escolha de stack | 6/10 | Trocar SQLite→Postgres, cortar Celery, adiar CrewAI |
| Divisão de agentes | 7/10 | Papéis certos, autonomia indefinida — ver A0–A4 |
| Sequência de implementação | 3/10 | Inverter: CRM → tools → 1 agente → multiagente |
| Rigor com mídia | 5/10 | xxHash+MHL, 3-2-1, proibição absoluta de formatar cartão |

O projeto é viável e a base está boa. O que muda o resultado é a ordem.
