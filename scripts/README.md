# Scripts

## `import_inventario.py` — carga do inventário

Lê o export do AssetTiger + a planilha de aluguel, reconcilia as duas, e gera um seed SQL
idempotente para a tabela `asset`.

```bash
python scripts/import_inventario.py \
  --assets asset.xlsx \
  --precos "Aluguel de Equipamentos.xlsx" \
  --out db/seed_inventario.sql
```

- Onde as planilhas discordam do valor, **vence a de aluguel** (é ela que gera preço) e a
  divergência é impressa para decisão humana.
- Descrições do AssetTiger são mantidas por serem mais específicas.
- `valor_reposicao` sai **NULL de propósito** — é decisão sua, não dado a importar.
- Rodar de novo atualiza campos e preserva ids e histórico (`ON CONFLICT DO UPDATE`).

Aplicar:

```bash
psql -d duck -f db/schema.sql
psql -d duck -f db/seed_inventario.sql
```

## `gerar_etiquetas.py` — etiquetas QR

```bash
python scripts/gerar_etiquetas.py --seed db/seed_inventario.sql --copias 2 --out etiquetas.html
```

Abrir no navegador → Ctrl/Cmd+P → **Salvar em PDF**, margens "nenhuma", escala 100%.

- Folha A4 com 3×7 = 21 etiquetas de 63,5 × 38,1 mm (Avery L7160 / Pimaco 6180).
- `--copias 2` gera duas por item: uma no corpo, outra no case.
- O QR carrega só o código (`0118`). Código curto lê rápido com câmera ruim e etiqueta amassada,
  que é a condição real de uso; URL longa aumenta a densidade e derruba a leitura.
- Correção de erro nível M: tolera etiqueta suja ou arranhada.
- **Imprima em poliéster ou vinil laminado.** Etiqueta de papel em case de equipamento não
  sobrevive a duas diárias.

## Dependências

```bash
pip install openpyxl segno
```
