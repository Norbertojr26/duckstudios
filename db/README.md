# Banco

- [`schema.sql`](schema.sql) — schema base do CRM (PostgreSQL 16)
- [`test_schema.sql`](test_schema.sql) — teste de fumaça das garantias críticas

## Aplicar

**A ordem importa.** `seed_inventario.sql` é carga mecânica das planilhas; os demais são camadas de
decisão aplicadas por cima. Reimportar as planilhas sem reaplicar as camadas desfaz as correções.

```bash
createdb duck
psql -d duck -v ON_ERROR_STOP=1 \
  -f db/schema.sql \
  -f db/seed_inventario.sql \
  -f db/seed_02_regras.sql \
  -f db/seed_03_catalogo.sql \
  -f db/seed_04_precos_servico.sql
```

| Arquivo | O que é | Origem |
|---|---|---|
| `seed_inventario.sql` | 156 itens | gerado das planilhas — não editar à mão |
| `seed_02_regras.sql` | correções de %, tarifa mensal, valor de reposição, cases, 10 kits, nomes do catálogo | **julgamento** |
| `seed_03_catalogo.sql` | 14 itens do catálogo sem cadastro, entram bloqueados | catálogo |
| `seed_04_precos_servico.sql` | 21 linhas de preço de serviço, pós, licenciamento e retainer | **proposta** |
| `seed_05_edicoes.sql` | o que você editou na planilha | gerado, não versionado |

Tudo é idempotente: rodar de novo atualiza e preserva ids e histórico.

## Editar sem escrever SQL

Valor de reposição, número de série, custo de sublocação e preço não moram em SQL — moram numa
planilha que você edita e devolve:

```bash
python scripts/exportar_planilha.py --db duck --out duck-editavel.xlsx   # exporta
#   ... edite as colunas AMARELAS no Excel/Numbers ...
python scripts/import_edicoes.py --xlsx duck-editavel.xlsx               # gera seed_05
psql -d duck -f db/seed_05_edicoes.sql                                   # aplica
```

A chave é sempre o `codigo` do item — não apague linhas nem mexa nessa coluna. As abas são
**Itens**, **Sublocados**, **Precos_locacao** e **Precos_servico**, com instruções na primeira aba.

## Testar

```bash
psql -d duck -f db/test_schema.sql
```

Resultado esperado (validado em PostgreSQL 16.13):

| Caso | Esperado |
|---|---|
| Reserva confirmada sem sobreposição | passa |
| Reserva confirmada **sobreposta** no mesmo item | `ERROR: conflicting key value violates exclusion constraint` |
| `asset_disponivel()` em período ocupado / livre | `f` / `t` |
| `deal` marcado como perdido sem `motivo_perda` | `ERROR: deal perdido exige motivo_perda` |
| View `equipamento_em_campo` | 1 linha, `atrasado = t` |
| Mesma bipada de QR sincronizada duas vezes | `ERROR: duplicate key ... conference_check_client_uuid_key` |

O segundo caso é a garantia central do módulo de locação: **overbooking é impossível no banco**,
independentemente de bug em aplicação ou agente.

O último caso é a garantia do app de conferência: o celular opera offline e sincroniza depois;
`client_uuid` faz a mesma bipada de QR reenviada não virar duas conferências.
