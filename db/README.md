# Banco

- [`schema.sql`](schema.sql) — schema base do CRM (PostgreSQL 16)
- [`test_schema.sql`](test_schema.sql) — teste de fumaça das garantias críticas

## Aplicar

```bash
createdb duck
psql -d duck -v ON_ERROR_STOP=1 -f db/schema.sql
```

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
