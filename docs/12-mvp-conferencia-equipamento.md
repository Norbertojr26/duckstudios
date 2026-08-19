# MVP — App de conferência de equipamento

**Objetivo:** em 2–3 semanas, ter no celular a resposta para "quem está com o quê, desde quando"
e um fluxo de conferência por scan **na saída e na volta**.

Este é o P0. Escopo deliberadamente pequeno.

---

## O problema em uma frase

O AssetTiger tem check-in mas não tem check-out: você só descobre que falta algo quando volta.
Com outros videomakers usando o equipamento na campanha, sua memória deixou de ser um sistema viável.

---

## Decisão técnica: PWA, não app nativo

| | PWA | Nativo (iOS + Android) |
|---|---|---|
| Prazo | dias | meses |
| Loja de app | não precisa | revisão da Apple/Google |
| Atualização | instantânea | release |
| Câmera/scanner | funciona | funciona |
| Offline | funciona (service worker + IndexedDB) | funciona |
| Código | um só | dois, ou React Native |

Você precisa disso **agora**, para você e alguns operadores conhecidos. PWA instalado na tela de
início resolve. Se um dia virar produto para terceiros, aí se discute nativo.

**Stack:** React + Vite (PWA) · `html5-qrcode` ou `BarcodeDetector` API · IndexedDB para fila offline ·
backend FastAPI + o Postgres que já está em `db/schema.sql` · Tailscale para acesso ao servidor.

---

## Etiquetagem

- QR Code com o `asset.codigo` (`DS-CAM-001`). Nada de URL longa — código curto lê rápido e com
  câmera ruim.
- **Etiqueta resistente:** poliéster ou vinil laminado. Etiqueta de papel em case de equipamento não
  sobrevive a duas diárias.
- Duas etiquetas por item: uma no corpo, outra no case/bolsa. Item dentro da bolsa não pode exigir
  abrir tudo para conferir.
- Itens pequenos (baterias, cartões, cabos): controlar por **quantidade em conjunto**, não por
  serial. Etiquetar cada cabo é o jeito mais rápido de abandonar o sistema na segunda semana.
- Se o AssetTiger já tem etiquetas coladas: reaproveitar os códigos existentes na importação.

---

## Telas (só 5)

### 1. "O que está fora agora" — tela inicial
Lista de saídas abertas: responsável, itens, desde quando, previsão de volta, atraso em vermelho.
Esta tela sozinha já substitui sua memória.

### 2. Nova saída
1. Quem leva (contato existente ou novo, com telefone)
2. Tipo: **locação paga · empréstimo · uso interno · subcontratação**
3. Previsão de devolução
4. **Escanear cada item** — lista cresce na tela, contador visível
5. Foto opcional do estado (obrigatória para item de alto valor)
6. Confirmar → gera termo

### 3. Termo e assinatura
Termo gerado com itens, seriais, valor de reposição, período e responsável.
Assinatura no dedo, na tela, na hora. PDF salvo e vinculado à saída.
Para empréstimo a amigo, um termo simplificado — mas **existe termo**.

### 4. Retorno
Abre a saída → escaneia cada item → a tela mostra em tempo real:
✅ conferido · ⬜ ainda falta · ⚠️ danificado.
Não deixa fechar com item faltando sem registrar o motivo.

### 5. Ficha do item
Histórico: onde esteve, com quem, danos, manutenção, receita gerada.

---

## Requisitos inegociáveis

- **Offline total.** Locação sem sinal é a regra, não a exceção. Toda ação grava local e sincroniza
  depois. Se o app precisar de internet para conferir uma saída, ele não serve.
- **Rápido.** Conferir 15 itens tem que levar menos de 2 minutos, ou ninguém usa quando está com
  pressa carregando van — que é exatamente quando o controle importa.
- **Multiusuário.** Os videomakers da campanha precisam conseguir devolver e conferir sem ser você.
- **Nunca fechar uma saída com item pendente sem registro explícito.**

---

## Fora do escopo do MVP (de propósito)

Precificação automática, integração financeira, emissão de NF, reserva futura com calendário,
notificação por WhatsApp, relatório de payback. Tudo isso é P1.

---

## Critério de sucesso

Duas semanas depois de instalado:

- [ ] 100% do inventário etiquetado e cadastrado
- [ ] Toda saída da campanha registrada pelo app, não pela memória
- [ ] Você consegue responder "quem está com a lente X?" pelo celular, em 5 segundos, sem sinal
- [ ] Pelo menos um outro videomaker fez uma devolução sozinho

Se em duas semanas você voltou a controlar de cabeça, o app está lento ou complicado demais —
o problema é o app, não a disciplina.

---

## Passos de implementação

| # | Etapa | Depende de |
|---|---|---|
| 1 | Exportar CSV do AssetTiger | você |
| 2 | Subir Postgres + `db/schema.sql`; importar inventário | 1 |
| 3 | Definir o que é serializado vs. quantidade | você |
| 4 | Gerar e imprimir etiquetas QR | 2, 3 |
| 5 | API de saída/retorno/consulta | 2 |
| 6 | PWA: telas 1, 2, 4 (o núcleo) | 5 |
| 7 | Etiquetar o parque fisicamente | 4 |
| 8 | Termo + assinatura (tela 3) | 6 |
| 9 | Usar na campanha e corrigir o que atrapalhar | 7, 8 |

Etapas 1 e 3 dependem de você e bloqueiam o resto — são as primeiras a destravar.
