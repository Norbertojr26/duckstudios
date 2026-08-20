# Duck Studios — CRM + Operação Assistida por Agentes

Base de conhecimento e código para dois projetos que na prática são **um só**:

1. **CRM operacional** do studio (serviços de filmagem/edição **+** locação de equipamento).
2. **Agentes** que executam tarefas repetitivas em cima desse CRM, rodando **localmente** num Mac Mini
   que viaja para locação (energia por bateria estacionária, internet por Starlink).

> A tese central deste repositório: **o CRM não é um projeto paralelo aos agentes — o CRM é a memória
> dos agentes.** Agente sem sistema de registro é agente que alucina o estado do mundo. Por isso o
> banco vem primeiro, os agentes vêm depois.

## Mapa dos documentos

| Arquivo | O que responde |
|---|---|
| [`docs/01-diagnostico-e-melhorias.md`](docs/01-diagnostico-e-melhorias.md) | Crítica direta à proposta inicial: o que está certo, o que quebra na prática |
| [`docs/02-arquitetura.md`](docs/02-arquitetura.md) | Como as peças se conectam (determinístico vs. LLM, offline-first) |
| [`docs/03-stack-decisoes.md`](docs/03-stack-decisoes.md) | Stack recomendada com trade-offs e o que **não** usar |
| [`docs/04-agentes-e-autonomia.md`](docs/04-agentes-e-autonomia.md) | Papéis dos agentes e níveis de autonomia (A0→A4) |
| [`docs/05-crm-modelo-dados.md`](docs/05-crm-modelo-dados.md) | Entidades do CRM + locação (o coração do sistema) |
| [`docs/06-roadmap.md`](docs/06-roadmap.md) | Ordem de implementação em fases, com critério de saída |
| [`docs/07-hardware-campo.md`](docs/07-hardware-campo.md) | Mac Mini + bateria + Starlink: números reais de energia e storage |
| [`docs/10-como-funciona-hoje.md`](docs/10-como-funciona-hoje.md) | **Retrato da operação atual** — receita, comercial, controle de equipamento |
| [`docs/11-necessidades-priorizadas.md`](docs/11-necessidades-priorizadas.md) | **Necessidades organizadas e priorizadas** (P0→P4) |
| [`docs/12-mvp-conferencia-equipamento.md`](docs/12-mvp-conferencia-equipamento.md) | **P0: spec do app de conferência com scan** |
| [`docs/13-analise-inventario.md`](docs/13-analise-inventario.md) | **Análise do parque real** — 156 itens, R$ 519.110, e o que está errado nas planilhas |
| [`docs/14-identidade-visual.md`](docs/14-identidade-visual.md) | **Identidade** extraída do catálogo → tokens do produto |
| [`docs/15-catalogo-vs-inventario.md`](docs/15-catalogo-vs-inventario.md) | **14 itens sublocados** que o catálogo vende e não são seus |
| [`docs/16-licenciamento-de-uso.md`](docs/16-licenciamento-de-uso.md) | **Como começar a cobrar cessão de uso** — receita recorrente sem produção nova |
| [`docs/17-deploy-railway.md`](docs/17-deploy-railway.md) | **Deploy** — Postgres, senha, domínio e o que testar |
| [`design/README.md`](design/README.md) | Logotipo, marca e `tokens.css` |
| [`scripts/README.md`](scripts/README.md) | Importador do AssetTiger e gerador de etiquetas QR |
| [`docs/99-perguntas-abertas.md`](docs/99-perguntas-abertas.md) | O que só você sabe responder — preencher antes da Fase 1 |
| [`sops/README.md`](sops/README.md) | **Como capturar e escrever SOPs** (o método, não só o formato) |
| [`sops/_TEMPLATE-SOP.md`](sops/_TEMPLATE-SOP.md) | Template v2 (o seu, corrigido e expandido) |
| [`db/schema.sql`](db/schema.sql) | Schema PostgreSQL executável do CRM (validado em PG 16) |

## SOPs já documentados

| ID | Processo | Estado |
|---|---|---|
| [SOP-001](sops/SOP-001-ingestao-cartao.md) | Ingestão e verificação de cartão (offload/DIT) | Rascunho — precisa dos seus dados reais |
| [SOP-002](sops/SOP-002-checkout-equipamento.md) | Check-out e check-in de locação de equipamento | Rascunho |
| [SOP-003](sops/SOP-003-orcamento-comercial.md) | Lead → orçamento → follow-up | Rascunho |

Rascunhos marcam com `<!-- PREENCHER -->` tudo que depende da sua operação real.

## Aplicação

No ar em `crm.duckstudios.com.br`. FastAPI + PostgreSQL, instalável como PWA e **funcionando sem
rede**: a bipada offline entra numa fila local e sobe sozinha, sem duplicar.

Módulos: painel · equipamento e kits · saídas e conferência por scan (câmera, leitor ou digitação) ·
funil, clientes e propostas com PDF · projetos · agentes. E **`/api/docs` — a mesma verdade das
telas, que é por onde os agentes leem e escrevem.**

Deploy em [`docs/17-deploy-railway.md`](docs/17-deploy-railway.md).

```bash
createdb duck && export DATABASE_URL=postgresql:///duck
pip install -r requirements.txt && python -m app.migrar && uvicorn app.main:app --reload
```

## Estado da carga

O inventário real está importado e validado em PostgreSQL 16: **156 itens, R$ 519.110** de
patrimônio, mais **14 itens bloqueados** que o catálogo vende sem cadastro. Em cima da carga
mecânica há três camadas de decisão — correções de preço, tarifa mensal, 10 kits (46% do
patrimônio), e a tabela de preços de serviço/licenciamento/retainer que não existia.
Ordem de aplicação em [`db/README.md`](db/README.md).

A identidade está completa: paleta da marca (teal `#018682`, laranja `#F18E25`), **Satoshi**,
9 SVGs do logotipo e o sistema de superfície escura macia — tudo em
[`design/tokens.css`](design/tokens.css). Telas de referência em
[`design/mock/`](design/mock/) usam os tokens reais e os dados reais do parque.

**Nada de valor mora em SQL.** Valor de reposição, número de série, custo de sublocação e preço
saem numa planilha editável e voltam para o banco — ver [`db/README.md`](db/README.md).

## Por onde começar

O primeiro entregável **não** é o CRM inteiro nem os agentes: é o
[app de conferência de equipamento](docs/12-mvp-conferencia-equipamento.md) (P0, 2–3 semanas).
Razão e priorização completa em [`docs/11-necessidades-priorizadas.md`](docs/11-necessidades-priorizadas.md).
