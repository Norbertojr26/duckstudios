#!/usr/bin/env python3
"""Extrai os logotipos vetoriais do Duck_logo.ai (que é um PDF por dentro) para SVG.

Um .ai não abre no navegador nem no Figma de todo mundo; SVG abre em tudo e entra direto no app,
na proposta e no termo. O texto do logotipo já está convertido em curvas no arquivo original, então
o SVG sai autossuficiente — não depende de ter a fonte instalada.

  python scripts/extrair_logos.py --ai Duck_logo.ai --out design/logo
"""
import argparse, re
from pathlib import Path
import pymupdf

# página do .ai -> (nome do arquivo, recorte)
#   'tudo'  = a prancheta inteira
#   'marca' = só a cabeça do marreco (primeiro bloco horizontal)
PAGINAS = {
    1: ("logo-horizontal-cor",      "tudo"),
    2: ("logo-horizontal-branco",   "tudo"),
    3: ("logo-horizontal-preto",    "tudo"),
    4: ("logo-empilhado-cor",       "tudo"),
    5: ("logo-empilhado-preto",     "tudo"),
    6: ("logo-empilhado-branco",    "tudo"),
}
MARCAS = {1: "marca-cor", 2: "marca-branco", 3: "marca-preto"}


def bbox_conteudo(page, margem=0.02):
    """União dos desenhos, ignorando retângulos que cobrem a prancheta inteira (o fundo)."""
    pr = page.rect
    r = pymupdf.Rect()
    for dr in page.get_drawings():
        d = dr["rect"]
        if d.width > pr.width * (1 - margem) and d.height > pr.height * (1 - margem):
            continue                      # é o fundo, não é o logo
        r |= d
    return r


def blocos_horizontais(page, folga=20):
    """Agrupa os desenhos em colunas separadas por espaço vazio — separa marca de logotipo."""
    caixas = sorted((dr["rect"] for dr in page.get_drawings()
                     if dr["rect"].width < page.rect.width * 0.98), key=lambda r: r.x0)
    grupos = []
    for c in caixas:
        if grupos and c.x0 - grupos[-1].x1 <= folga:
            grupos[-1] |= c
        else:
            grupos.append(pymupdf.Rect(c))
    return grupos


def svg_recortado(page, rect, pad=8):
    """SVG da página com o retângulo de fundo removido e a viewBox no conteúdo."""
    svg = page.get_svg_image(text_as_path=True)

    # O fundo é um <path> que cobre a prancheta inteira. Existe um path parecido dentro de
    # <defs> (o clipPath da página) que NÃO pode ser tocado — apagá-lo zera o clip e some com
    # o desenho todo. Por isso a remoção só vale depois da abertura da camada.
    marca_camada = "<g inkscape:groupmode=\"layer\""
    corte = svg.index(marca_camada)
    cabeca, corpo = svg[:corte], svg[corte:]
    largura = page.rect.width

    def e_fundo(m):
        """True se o <path> descreve um retângulo que cobre quase toda a prancheta."""
        nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", m.group("d"))]
        if len(nums) < 4:
            return False
        xs = nums[0::2] + [nums[2]]
        return (max(xs) - min(xs)) > largura * 0.95

    corpo = re.sub(r'<path transform="matrix\(1,0,0,-1,0,[\d.]+\)" d="(?P<d>M[^"]+Z)"\s*/>\s*',
                   lambda m: "" if e_fundo(m) else m.group(0), corpo, count=1)
    svg = cabeca + corpo

    x, y = rect.x0 - pad, rect.y0 - pad
    w, h = rect.width + 2 * pad, rect.height + 2 * pad
    return re.sub(r'width="[\d.]+" height="[\d.]+" viewBox="[\d.\- ]+"',
                  f'width="{w:.0f}" height="{h:.0f}" viewBox="{x:.2f} {y:.2f} {w:.2f} {h:.2f}"',
                  svg, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", required=True)
    ap.add_argument("--out", default="design/logo")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(a.ai)

    for i, (nome, modo) in PAGINAS.items():
        page = doc[i]
        rect = bbox_conteudo(page)
        (out / f"{nome}.svg").write_text(svg_recortado(page, rect), encoding="utf-8")
        print(f"{nome}.svg  ({rect.width:.0f}x{rect.height:.0f})")

    for i, nome in MARCAS.items():
        page = doc[i]
        blocos = blocos_horizontais(page)
        if not blocos:
            print(f"AVISO: nenhum bloco em p{i+1}, {nome} não gerado"); continue
        (out / f"{nome}.svg").write_text(svg_recortado(page, blocos[0]), encoding="utf-8")
        print(f"{nome}.svg  ({blocos[0].width:.0f}x{blocos[0].height:.0f})")


if __name__ == "__main__":
    main()
