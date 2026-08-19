---
id: SOP-001
titulo: "Ingestão e verificação de cartão (offload/DIT)"
versao: 1
dono_humano: ""            # <!-- PREENCHER -->
area: dit
criticidade: critica
reversibilidade: irreversivel   # material bruto perdido não se refilma
frequencia: ""             # <!-- PREENCHER: quantas diárias/mês? -->
tempo_manual_min: 0        # <!-- PREENCHER -->
autonomia_alvo: A3
atualizado_em: 2026-01-01
depende_de: []
---

# SOP-001 — Ingestão e verificação de cartão

> **Rascunho.** Tudo marcado `<!-- PREENCHER -->` depende da sua operação real. A estrutura,
> as verificações e as proibições já valem como estão.

## 0. Objetivo e escopo

- **Resultado:** todo frame gravado numa diária existe verificado em **≥ 2 destinos físicos
  distintos**, catalogado no CRM, com proxies prontos para edição — antes de qualquer cartão voltar
  para circulação.
- **No escopo:** cópia verificada, manifesto de hash, estrutura de pastas, extração de metadados,
  proxies, registro no CRM, relatório.
- **Fora do escopo:** formatação de cartão (**sempre humano, na câmera**), decupagem, seleção de
  takes, backup off-site (SOP futuro).

## 1. Gatilho

| Tipo | Detalhe |
|---|---|
| Evento | volume montado em `/Volumes/*` contendo estrutura de câmera reconhecida (`DCIM/`, `PRIVATE/`, `CLIP/`, `XDROOT/`, `RDM/`) |
| Comando | `duck ingest --projeto <slug> --camera <A\|B\|...> [--data YYYY-MM-DD]` |
| Mensagem | Telegram: "descarrega o cartão da B do <projeto>" → agente resolve para o comando acima |

- **Impedimentos:** já existe execução ativa para o mesmo `card_uuid`; nenhum projeto ativo
  identificável; destino não montado.

## 2. Contrato de dados

**Entrada**
```json
{
  "volume_path": "string — caminho do volume montado — obrigatório",
  "projeto_id": "uuid — projeto no CRM — obrigatório",
  "camera": "string — rótulo da câmera (A, B, DRONE, GOPRO1) — obrigatório",
  "data_filmagem": "date — default: data mais antiga entre os arquivos",
  "destinos": ["string — ≥2 caminhos de destino — obrigatório"],
  "dry_run": "bool — default false"
}
```

**Saída**
```json
{
  "status": "sucesso | parcial | falha | escalado",
  "trace_id": "uuid",
  "resultado": {
    "offload_id": "uuid",
    "card_uuid": "string",
    "arquivos": 0,
    "bytes": 0,
    "duracao_total_seg": 0,
    "destinos_verificados": [],
    "mhl_paths": [],
    "proxies_gerados": 0,
    "divergencias": []
  },
  "avisos": [],
  "acao_humana_necessaria": null
}
```

**Estado persiste em:** tabela `media_offload` + `media_file` (ver `db/schema.sql`) e no arquivo
`_INGEST/relatorio.json` gravado junto à mídia.

## 3. Pré-requisitos

| Recurso | Verificação |
|---|---|
| Origem | volume montado **somente-leitura** e legível |
| Destinos | ≥2 montados, cada um com espaço ≥ `tamanho_origem × 1.3` |
| Ferramentas | `rsync`, `xxhsum` (ou `ascmhl`), `ffmpeg`, `exiftool`, `mediainfo` |
| CRM | conexão OK, `projeto_id` existe e está ativo |
| Energia | se em bateria: carga ≥ 40% ou fonte conectada — senão, escalar |

## 4. Regras de negócio e taxonomia

**Estrutura de destino (proposta — validar):**

```
/{DESTINO}/{ANO}/{PROJETO_SLUG}/{YYYY-MM-DD}_{DIARIA_NN}/
    ├── RAW/
    │   └── {CAMERA}/{CARD_NN}/        ← espelho fiel do cartão, nunca alterado
    ├── PROXIES/{CAMERA}/
    ├── AUDIO/
    ├── FOTO/
    ├── DOCS/                          ← ordem do dia, decupagem, claquete
    └── _INGEST/                       ← manifestos MHL, logs, relatorio.json
```

<!-- PREENCHER: qual estrutura você usa HOJE? Precisamos migrar ou adotar? -->
<!-- PREENCHER: quais câmeras/codecs? (ex: FX3 XAVC-I, R5 CRM, drone, GoPro) -->
<!-- PREENCHER: qual NLE? Premiere ou Resolve? Muda o formato de proxy e a estrutura esperada. -->

**Regras invioláveis de nomenclatura:**

- **Nunca renomear arquivo dentro de `RAW/`.** O nome original da câmera é chave de relação com
  metadados, arquivos-irmão (`.XML`, `.THM`, `.CPI`) e clipes segmentados. Renomeação acontece em
  `PROXIES/`, nunca no bruto.
- Colisão de nome entre cartões é resolvida pela pasta `{CARD_NN}`, não por sufixo no arquivo.
- `CARD_NN` é sequencial por câmera por diária (`01`, `02`, ...).

**Triagem:** nada é descartado automaticamente na ingestão. Arquivos suspeitos (0 byte, duração 0,
metadata ilegível) são **copiados normalmente** e listados em `divergencias` para revisão humana.

> Motivo: descarte automático em ingestão é a única classe de bug deste SOP que não tem desfazer.

## 5. Fluxo passo a passo

| # | Passo | Tipo | Aut. | Verificação |
|---|---|---|---|---|
| 1 | Montar origem como somente-leitura; capturar `card_uuid`, serial, capacidade | `[DET]` | A3 | volume acessível, uuid capturado |
| 2 | Inventariar origem: lista de arquivos, tamanhos, contagem, bytes totais | `[DET]` | A3 | contagem > 0 |
| 3 | Resolver projeto/câmera/diária (mensagem humana → IDs do CRM) | `[LLM]` | A2 | IDs existem; ambiguidade → perguntar |
| 4 | Checar espaço em todos os destinos | `[DET]` | A3 | espaço ≥ origem × 1.3 em cada |
| 5 | Criar árvore de destino; abortar se já existir com conteúdo divergente | `[DET]` | A3 | pastas criadas |
| 6 | Copiar para **destino 1** com verificação (`rsync` + hash xxHash64 por arquivo) | `[DET]` | A3 | 100% dos hashes conferem |
| 7 | Copiar para **destino 2** (a partir da origem, não do destino 1) | `[DET]` | A3 | 100% dos hashes conferem |
| 8 | Gerar manifesto **ASC MHL** em cada destino | `[DET]` | A3 | MHL válido, cobre todos os arquivos |
| 9 | Extrair metadados (codec, resolução, fps, timecode, lente, duração) → CRM | `[DET]` | A3 | linha por arquivo em `media_file` |
| 10 | Gerar proxies (`ffmpeg`) com nomenclatura de edição | `[DET]` | A3 | 1 proxy por clipe de vídeo |
| 11 | Registrar `media_offload` como `verificado` | `[DET]` | A3 | registro gravado |
| 12 | Escrever `_INGEST/relatorio.json` + relatório em português | `[LLM]` | A3 | arquivo existe |
| 13 | Notificar operador: "cartão X liberado para formatação" | `[LLM]` | A3 | mensagem entregue |
| 14 | **Formatar cartão** | HUMANO | **A0** | nunca automatizado |

**Passo 6/7 em detalhe (por que duas cópias a partir da origem):** copiar destino 1 → destino 2
propaga silenciosamente um erro de leitura ocorrido na primeira cópia. Ler duas vezes da origem
custa tempo e detecta cartão com setor ruim.

## 6. Proibições absolutas

- [ ] **NUNCA** formatar, apagar ou escrever no cartão de origem — nem com 100% dos hashes conferidos.
- [ ] **NUNCA** usar `rsync --delete`, `rm -rf` ou mover (`mv`) dentro de `RAW/`.
- [ ] **NUNCA** renomear arquivo em `RAW/`.
- [ ] **NUNCA** declarar conclusão com menos de 2 destinos verificados.
- [ ] **NUNCA** descartar arquivo automaticamente, mesmo corrompido ou com 0 byte.
- [ ] **NUNCA** prosseguir com hash divergente sem registrar e notificar.
- [ ] **NUNCA** ejetar volume antes da verificação terminar.

## 7. Definition of Done

- [ ] `count(arquivos)` e `sum(bytes)` idênticos entre origem e **cada** destino
- [ ] 100% dos arquivos com xxHash64 conferido em **cada** destino
- [ ] Manifesto ASC MHL gravado e validado em cada destino
- [ ] `media_offload.status = 'verificado'` e `media_file` populada
- [ ] Proxies gerados para todos os clipes de vídeo
- [ ] Relatório escrito e notificação enviada
- [ ] Lista de divergências vazia — ou explicitamente revisada por humano

**Só então** o cartão entra na fila de "liberado para formatação" — que é ato humano.

## 8. Idempotência e retomada

- **Chave de dedupe:** `(card_uuid, projeto_id, data_filmagem)`.
- **Rodar 2×:** verifica hashes existentes e copia apenas o que falta. Nunca duplica pasta nem
  cria `_2`.
- **Queda no meio:** cada arquivo verificado é gravado em `media_file` na hora; retomada pula os já
  conferidos. Um `offload` em `em_progresso` há mais de 6h é marcado `interrompido` e sinalizado.
- **Sem rede:** ingestão **deve** concluir 100% offline. Escritas no CRM vão para fila local e
  sincronizam depois. Nenhum passo pode depender da Starlink.

## 9. Exceções e escalonamento

| Condição | Ação | Notificar | Bloqueia? |
|---|---|---|---|
| Destino > 90% ocupado | pausar antes de iniciar | operador | sim |
| Menos de 2 destinos disponíveis | copiar para 1 e marcar `parcial`; **não** liberar cartão | operador + dono | sim (para liberação) |
| Hash divergente num arquivo | recopiar até 2×; persistindo, isolar em `_INGEST/suspeitos/` e seguir | operador + DIT | não |
| Erro de leitura no cartão | parar imediatamente, não reler em loop, preservar o já copiado | operador (urgente) | sim |
| Projeto ambíguo | perguntar ao humano; enquanto isso copiar para `_INBOX/` já verificado | operador | não |
| Bateria < 20% em campo | concluir arquivo atual, pausar, salvar checkpoint | operador | sim |
| Timeout: sem progresso por 15 min | escalar | operador | sim |

## 10. Observabilidade

- Log estruturado por `trace_id`: cada arquivo, bytes, hash origem/destino, tempo, decisões `[LLM]`.
- Cópia do log junto à mídia em `_INGEST/` — a auditoria tem que sobreviver à perda do banco.
- **Métricas:** MB/s por destino · % execuções sem intervenção · nº de divergências por 1000 arquivos
  · tempo entre fim da diária e cartão liberado.

## 11. Casos de teste

| # | Cenário | Entrada | Esperado |
|---|---|---|---|
| 1 | Caminho feliz | 1 cartão 128GB, câmera A, projeto conhecido | 2 destinos verificados, proxies, cartão liberado |
| 2 | Cartão parcialmente já ingerido | mesmo `card_uuid` de execução interrompida | copia só o faltante, sem duplicar |
| 3 | Segundo destino ausente | apenas 1 destino montado | `status=parcial`, cartão **não** liberado |
| 4 | Arquivo corrompido | 1 clipe com hash divergente | isolado, notificado, demais concluídos |
| 5 | Projeto ambíguo | "descarrega o cartão" sem contexto | pergunta ao humano, não adivinha |

<!-- PREENCHER: substituir por 3 execuções REAIS do mês passado, com nomes e caminhos verdadeiros -->

## 12. Histórico

| Versão | Data | Mudança | Motivo |
|---|---|---|---|
| 1 | 2026-01 | criação | base para automação |
