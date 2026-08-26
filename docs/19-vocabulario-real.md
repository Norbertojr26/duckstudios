# Vocabulário e estrutura reais (capturados do Finder e do Premiere)

Fonte primária: prints do Finder e do painel de projeto do Premiere, 26/08/2026, mais a
descrição do dono. Este documento **prevalece sobre suposições anteriores** — inclusive sobre
partes do SOP oficial.

> Em construção: o dono está descrevendo projeto a projeto. O que já está confirmado entra aqui;
> o que falta está marcado.

---

## 1. O fluxo editorial real tem QUATRO estados, não três

| Cor no Finder | Significado (palavras do dono) | Estado no sistema |
|---|---|---|
| 🔴 Vermelho | não iniciado, mas os arquivos estão na pasta | `ingerido` |
| 🟡 Amarelo | edição iniciada | `em_edicao` |
| 🟢 Verde | aprovado | `aprovado` |
| 🟣 Roxo | subido no Drive | `entregue` |

O documento oficial do SOP descrevia só três e errava os rótulos. O sistema agora usa estes
quatro (`project.estado_editorial`), com as mesmas cores na tela de Projetos.

**Consequência importante para o arquivamento:** no documento oficial, o Verde disparava
arquivar+deletar. No fluxo real, Verde é só *aprovado* — ainda vem o upload (Roxo). O gatilho de
arquivamento correto é o **Roxo**, e mesmo assim com as salvaguardas do docs/18 (hash no destino
frio antes de deletar qualquer coisa).

## 2. A hierarquia real é CLIENTE → JOB

```
/Projetos/
  ├── ATRICON/                       🟡
  ├── Banco de Imagem/               ← transversal: não é cliente, é acervo
  │     ├── FEIRA DO PARAGUAI/  🟢
  │     ├── PLANALTINA/         🟢
  │     └── SOBRADINHO/         🟢
  ├── Celina Leão/                   🟢
  ├── Cláudio Abrantes/
  ├── Marcela Passamani/
  │     ├── Inserções TV/       🟢
  │     ├── Perguntas e respostas/ 🟢
  │     └── Portraits Mulheres/ 🟢
  ├── MASTER BUNDLE/                 ← transversal (a confirmar o que é)
  └── Zé Humberto/
        ├── 16 AGOSTO - ZH/     🔴
        ├── Campanha TV/        🔴
        ├── Carona 2/           🟣
        └── Carona 3/           🟣
```

Observações que mudam o modelo:

- **A pasta de topo é o CLIENTE** (pessoa/organização), não `[ANO]_[CLIENTE]_[PROJETO]` como o
  SOP oficial propunha. O job vive dentro do cliente. No CRM isso já existe: `company` → `project`.
- **A tag pode estar nos dois níveis** (ATRICON está amarela no nível do cliente). O sistema
  trata estado por `project`; cliente com um job só é o caso comum.
- **Nomes de job são livres** ("16 AGOSTO - ZH", "Carona 2") — o vínculo pasta↔projeto no CRM é
  por `pasta_raiz` (caminho literal) com fallback de busca pelo slug, nunca por convenção rígida
  de nome. Convenção nova só para projetos novos, sem renomear o passado.
- **Pastas transversais** (Banco de Imagem, MASTER BUNDLE) não são jobs — não entram no fluxo de
  estado. O Banco de Imagem por cidade (Feira do Paraguai, Planaltina, Sobradinho) é acervo
  reutilizável; candidato natural a virar entidade própria depois (busca de b-roll por cidade).
- O trabalho é fortemente **institucional/político** (inserções de TV, campanha, "carona" —
  termos de mídia eleitoral). Isso conversa com o Ramo B do agente comercial e com licenciamento.

## 3. Dentro do Premiere (padrão de bins)

```
ASSETS/   (Animation Composer, IMGS, ITEMS, Mídia do modelo de ani, OVERLAY VHS)
AUDIOS/   (SFX, GRAVADOR, MUSICAS)
SEQ/      (sequências com versão: "Antes x Depois V1", "V2" · SUBS/SYNC)
VIDEOS/   (por câmera: AVATA 2, FX3, FX30, INSERTS INTERNET)
```

- **VIDEOS organizado POR CÂMERA** — confirma a estrutura `{CAMERA}/` do SOP-001.
- **Versionamento é na sequência** (V1, V2…) — casa com `deliverable_version`.
- Os bins têm cor própria (laranja=pasta, verde=sequência) — vocabulário visual consistente.

## 4. O que o sistema já absorveu

- `project.estado_editorial` com os 4 estados e as cores reais — visível e editável em `/projetos`
- `POST /api/projetos/{slug}/estado` — transição vinda de fora (o Mac)
- [`scripts/mac/refletir_tags.py`](../scripts/mac/refletir_tags.py) — roda no Mac Mini:
  `refletir` pinta as pastas com a cor da fase no CRM; `capturar` lê a tag que o editor mudou na
  mão e registra a transição no CRM com autor `mac:finder-tag`. O editor continua trabalhando
  como sempre trabalhou — o Finder vira interface do sistema, não concorrente.

## 5. A confirmar (aguardando a descrição digitada)

- [ ] O que varia de projeto para projeto ("cada projeto fica meio diferente" — variar onde?)
- [ ] O que é o **MASTER BUNDLE**
- [ ] Onde ficam **proxies** hoje (existem? por projeto?)
- [ ] Estrutura da pasta de um job por dentro (bruto? exports? projeto do Premiere?)
- [ ] Como é a estrutura no **Drive** quando sobe (Roxo) — espelha a local?
- [ ] "INSERTS INTERNET" dentro de VIDEOS — material baixado? De onde? (direitos!)
