# Como capturar e escrever SOPs

O template é o formato. Isto aqui é o **método** — como tirar o processo da sua cabeça e colocar no
papel sem gastar um mês.

## 1. Escolher o que documentar primeiro

Não documente tudo. Pontue cada tarefa e ataque as de maior pontuação:

```
prioridade = frequencia_mensal × minutos_por_execucao × (1 + risco_de_erro)
```

- `risco_de_erro`: 0 = errar não dói · 1 = retrabalho · 3 = cliente percebe · 5 = perde material/dinheiro

Regra prática: **as três primeiras SOPs devem ser tarefas que você faz semanalmente e odeia.**
Se a primeira automação não te devolver tempo em duas semanas, o projeto morre por desânimo.

Candidatas prováveis no seu caso (validar com a matriz):

| Área | Processo |
|---|---|
| DIT | Ingestão + verificação de cartão · backup 3-2-1 · geração de proxies · preparo de projeto no NLE |
| Pós | Entrega/versionamento para aprovação · arquivamento e política de retenção |
| Rental | Cotação com checagem de disponibilidade · check-out · check-in e vistoria de dano · manutenção |
| Comercial | Qualificação de lead · orçamento · follow-up · contrato e sinal |
| Financeiro | Fechamento de custos de diária · emissão de NF/cobrança · conciliação |

## 2. Capturar (30–40 min por SOP, não mais)

O erro é tentar escrever o SOP de memória, sentado. Não funciona: você omite justamente os detalhes
automáticos, que são os que o agente precisa.

**Faça assim, na próxima vez que executar a tarefa de verdade:**

1. **Grave a tela + narre em voz alta** enquanto faz (QuickTime já basta). Fale o que está pensando,
   principalmente nos momentos de decisão: *"esse aqui eu jogo fora porque..."*.
2. Tire **print da estrutura de pastas** antes e depois.
3. Anote **toda vez que hesitou** — hesitação é regra de negócio não escrita.
4. Transcreva a narração e jogue no template. Vale usar um LLM para transformar transcrição em
   rascunho de SOP; você só revisa.

## 3. As 8 perguntas que fecham qualquer SOP

Se o rascunho responde a estas oito, ele está pronto para virar código:

1. O que **exatamente** faz isso começar?
2. Como eu sei que **terminou certo**? (tem que ser verificável por máquina)
3. Qual passo, se eu errar, **não tem volta**?
4. O que eu faço quando **dá errado** — e a quem eu aviso?
5. Que informação eu **consulto** no meio do caminho, e de onde ela vem?
6. Que decisão eu tomo aqui que **um script não conseguiria tomar**? (esses são os `[LLM]`)
7. Se eu parar na metade e voltar amanhã, **como eu sei onde parei**?
8. Me dá **três execuções reais** desse processo, do mês passado.

## 4. Vocabulário — o passo que quase todo mundo pula

Antes de escrever a primeira SOP, escreva o glossário. O agente precisa saber que "a B" é a segunda
câmera, que "diária" pode ser dia de filmagem *ou* valor pago ao freela, que "bruto" é RAW e
"final" é entrega aprovada, e que o cliente "Prefeitura" no seu WhatsApp é o cadastro
`Prefeitura Municipal de X` no CRM.

Ambiguidade de vocabulário é a origem de grande parte dos erros de agente — e é barata de eliminar.

## 5. Ciclo de vida de um SOP

```
rascunho → validado em dry-run → automatizado em A1 (sugere)
        → A2 (executa com aprovação) → A3 (executa e reporta) → revisão trimestral
```

Um SOP só sobe de autonomia com **evidência**: 10 execuções consecutivas sem correção humana.
Se corrigir, volta um nível e o motivo entra no histórico do SOP.

## 6. Regra de ouro

> Se o SOP não puder ser executado por um freelancer competente que nunca pisou no seu studio,
> ele também não pode ser executado por um agente.

O agente não é mais esperto que o texto que você deu a ele — é só mais rápido e mais literal.
