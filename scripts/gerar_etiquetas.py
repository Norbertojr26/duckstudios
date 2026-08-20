#!/usr/bin/env python3
"""Gera folha A4 de etiquetas QR para o parque de equipamento.

Layout: 3 colunas x 7 linhas de 63,5 x 38,1 mm (Avery L7160 / Pimaco 6180) = 21 por folha.
Saída: HTML pronto para imprimir (Ctrl+P -> Salvar em PDF, margens "nenhuma", escala 100%).

O QR carrega só o código do item ("0118"). Código curto lê rápido com câmera ruim, na correria,
com a etiqueta amassada — que é exatamente a condição de uso. URL longa dentro do QR aumenta a
densidade do código e derruba a taxa de leitura.

  python scripts/gerar_etiquetas.py --seed db/seed_inventario.sql --copias 2 --out etiquetas.html
"""
import argparse, io, re, html
import segno

TPL_HEAD = """<title>Etiquetas QR — Duck Studios</title>
<style>
  @page { size: A4; margin: 0; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, Helvetica, Arial, sans-serif;
         background: #fff; color: #000; }
  .folha { width: 210mm; height: 297mm; padding: 12.7mm 7.75mm; display: grid;
           grid-template-columns: repeat(3, 63.5mm); grid-auto-rows: 38.1mm;
           page-break-after: always; }
  .et { display: flex; align-items: center; gap: 2.5mm; padding: 2.5mm 3mm;
        overflow: hidden; }
  .et svg { width: 26mm; height: 26mm; flex: none; }
  .txt { min-width: 0; }
  .tag { font-size: 16pt; font-weight: 700; letter-spacing: .5px; line-height: 1; }
  .nome { font-size: 7pt; line-height: 1.15; margin-top: 1.2mm;
          display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
          overflow: hidden; }
  .marca { font-size: 6pt; text-transform: uppercase; letter-spacing: .6px;
           margin-top: .8mm; opacity: .65; }
  @media screen { body { background: #555; padding: 8mm 0; }
                  .folha { background: #fff; margin: 0 auto 8mm; outline: 1px solid #000; } }
</style>
"""


def qr_svg(code):
    buf = io.BytesIO()
    # error correction M: aguenta etiqueta suja/arranhada sem inflar o código
    segno.make(code, error="m").save(buf, kind="svg", svgclass=None, lineclass=None,
                                     omitsize=True, xmldecl=False, svgns=True, border=0)
    return buf.getvalue().decode("utf-8")


def ler_seed(path):
    """Lê os VALUES do seed gerado por import_inventario.py."""
    txt = open(path, encoding="utf-8").read()
    itens = []
    for m in re.finditer(r"\(\s*'([^']+)',\s*'((?:[^']|'')*)',\s*'((?:[^']|'')*)',\s*"
                         r"'((?:[^']|'')*)'", txt):
        tag, nome, _cat, marca = (g.replace("''", "'") for g in m.groups())
        itens.append((tag, nome, marca))
    return itens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="db/seed_inventario.sql")
    ap.add_argument("--copias", type=int, default=2,
                    help="etiquetas por item (2 = uma no corpo, uma no case)")
    ap.add_argument("--out", default="etiquetas.html")
    a = ap.parse_args()

    itens = ler_seed(a.seed)
    if not itens:
        raise SystemExit(f"nenhum item lido de {a.seed}")

    et = []
    for tag, nome, marca in itens:
        for _ in range(a.copias):
            et.append(f'<div class="et">{qr_svg(tag)}<div class="txt">'
                      f'<div class="tag">{html.escape(tag)}</div>'
                      f'<div class="nome">{html.escape(nome)}</div>'
                      f'<div class="marca">{html.escape(marca)}</div></div></div>')

    folhas = ["".join(et[i:i + 21]) for i in range(0, len(et), 21)]
    corpo = "".join(f'<div class="folha">{f}</div>' for f in folhas)
    open(a.out, "w", encoding="utf-8").write(TPL_HEAD + corpo)
    print(f"{len(itens)} itens x {a.copias} = {len(et)} etiquetas em {len(folhas)} folhas -> {a.out}")


if __name__ == "__main__":
    main()
