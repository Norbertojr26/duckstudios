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
