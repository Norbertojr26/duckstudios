# Análise do SOP oficial (v1.0 — Produção & Cloud CRM)

Documento recebido em 26/08: 5 módulos — DIT/mídia, atendimento comercial com IA, locadora web,
gestão patrimonial e revisão/entrega/portfólio. Esta análise diz o que está forte, o que quebra,
e o que cada módulo vira em agente.

---

## O que o documento acerta

1. **Cobre a operação inteira, ponta a ponta.** Do cartão na câmera ao portfólio no site, com
   gatilhos explícitos por módulo. É raro um SOP de produtora fechar o ciclo assim.
2. **A bifurcação comercial é a decisão mais inteligente do documento.** Eventos = escopo →
   equipe; Publicidade = verba → melhor entrega possível dentro dela. A filosofia do Ramo B
   ("não cobrar o mínimo para entregar o básico") é posicionamento de gente grande e conversa
   direto com o cliente de retainer que você quer.
3. **O Módulo 4 já existe** — é o app que está no ar (scan, custódia, prazos, termo). O documento
   valida a direção do que foi construído.
4. **Escolhas pragmáticas de ferramenta**: Vimeo para review com timecode, Drive transitório com
   expiração, régua de notificações. Nada exótico, tudo operável.

## Os 4 pontos que quebram — e como corrigir

### 1. 🔴 O fluxo de mídia termina com UMA cópia do bruto

O Módulo 1 faz uma cópia verificada para o storage, e no arquivamento **move** o RAW para o cold
storage e deleta os proxies. Em nenhum momento do ciclo existem duas cópias independentes do
material bruto. Se o HD de arquivo morrer — e HD de arquivo morre — o projeto acabou, e bruto
não se refilma.

**Correção:** regra 3-2-1 desde a ingestão — o cartão só é liberado com o material verificado em
**≥ 2 destinos físicos**, e o arquivamento *copia+verifica* no destino frio **antes** de qualquer
deleção, nunca *move*. O [SOP-001 do repositório](../sops/SOP-001-ingestao-cartao.md) já exige
isso; o documento oficial precisa absorver.

### 2. 🔴 Finder Tags como máquina de estado

Usar a cor da pasta como estado do projeto é visualmente ótimo e estruturalmente frágil:

- a tag é metadado do macOS — **o CRM e os agentes não a enxergam**, então o estado do projeto
  vive fora do sistema que precisa dele;
- copiar a pasta para exFAT/NTFS/NAS **perde a tag silenciosamente**;
- não há histórico: quem mudou, quando, por quê;
- e o gatilho mais destrutivo do fluxo (arquivar + **deletar**) dispara por um gesto de um
  clique, sem confirmação e sem verificação.

O próprio documento mostra o sintoma: a tag Vermelha está rotulada "In_Progress", e Amarela e
Verde estão **ambas** rotuladas "Approved_Delivered" — erro de cópia que ninguém percebeu porque
prosa não valida.

**Correção:** o estado mora no Postgres (`project.status`), com histórico em `activity`. A tag
do Finder vira **reflexo** — um script aplica a cor a partir do banco, para o editor continuar
vendo o status na pasta. E deleção nunca é gatilhada por tag: exige hash conferido no destino
frio + aprovação explícita.

### 3. 🟡 MD5 e a performance da ingestão

MD5 num offload de TBs em campo é gargalo de CPU e de bateria. O documento já cita xxHash como
alternativa — fixar: **xxHash64** para velocidade + manifesto **ASC MHL** para
interoperabilidade com pós-produção de terceiros (Silverstack/ShotPut/Hedge leem).

### 4. 🟡 Os fluxos não têm contrato

Os módulos descrevem *o que* acontece, mas não: entrada/saída de cada passo, o que acontece se
rodar duas vezes, o que acontece se cair na metade, quem aprova o quê, e os casos de teste. Sem
isso, "automação" vira script que funciona no dia bom. O template
[`sops/_TEMPLATE-SOP.md`](../sops/_TEMPLATE-SOP.md) existe para isso — cada módulo do documento
oficial deve ganhar a versão estruturada (I/O, idempotência, autonomia por passo, golden runs).

## Ajustes menores por módulo

| Módulo | Ajuste |
|---|---|
| 2 (IA comercial) | Regras porte→equipe viram **dados** (tabela), não prosa no prompt — implementado. O LLM nunca fala preço; preço sai da `price_list` com aprovação — implementado como teto A2. WhatsApp API oficial exige verificação Meta Business + aprovação de templates: tratar como integração à parte, não como bloqueio do agente |
| 3 (locadora web) | Site sem preço é decisão comercial válida, mas o carrinho deve **criar deal + hold no CRM** e checar disponibilidade contra `rental_line` na hora — a constraint anti-overbooking já garante o resto |
| 4 (patrimônio) | Já no ar. Faltavam termo assinado (feito hoje) e a régua de notificações (feito hoje — agente Rental) |
| 5 (entrega) | A limpeza do Drive em 15–30 dias pode ser job automático com aprovação, em vez de "alerta para o operador"; a ficha técnica do portfólio o CRM gera sozinho a partir de `project` |

## De módulo a agente — o mapa

| Módulo do SOP | Agente | Estado |
|---|---|---|
| 2 — Qualificação comercial | **Comercial** | ✅ implementado — `POST /api/agentes/comercial/qualificar` |
| 4 — Régua de devoluções | **Rental** | ✅ implementado — roda a cada 15 min + botão manual |
| 1 — Ingestão/DIT | **DIT** | próximo — precisa do Mac Mini (acesso físico a volumes) |
| 5 — Entrega/portfólio | **Entrega** | depois — depende de credenciais Vimeo/Drive |
| 3 — Carrinho web | entrada do Comercial | o formulário do site chama o mesmo endpoint com `canal=site` |

### Como os dois agentes de hoje funcionam

**Rental (determinístico, sem LLM de propósito).** Prazo e cobrança são o pior lugar para um
modelo inventar frase. As condições são SQL (devolve hoje / atrasou), a mensagem é template, e o
agente é idempotente — rodar dez vezes no mesmo dia cria **uma** aprovação por saída. Autonomia
A2: ele redige, você aprova na tela `/agentes`, e só então a mensagem entra na `outbox`.

**Comercial (LLM onde linguagem é o problema).** Classifica o ramo, extrai os campos do texto
livre e redige o rascunho — com **saída estruturada validada por schema**, então campo faltando
ou formato errado não passa. Contato e negócio são criados por código com dedupe (telefone
E.164; 1 deal por contato por semana). Regras invioláveis no sistema do agente: nunca cita
preço, nunca confirma data, nunca promete prazo. E o rascunho **sempre** vira aprovação — A2 é
teto, não fase.

Toda execução de qualquer agente grava em `agent_run`/`agent_action`: qual ferramenta, com que
argumentos, o que voltou, tokens gastos. É o que permite subir autonomia por evidência.

### O que falta para o Comercial atender de verdade

1. `ANTHROPIC_API_KEY` nas variáveis do serviço (sem ela o endpoint responde 503 explicando);
2. o conector de WhatsApp (Meta Cloud API ou um gateway tipo Evolution/Z-API) apontando o
   webhook para `/api/agentes/comercial/qualificar`;
3. um worker de envio para a `outbox` — hoje a mensagem aprovada fica na fila, honestamente
   marcada como aguardando canal.
