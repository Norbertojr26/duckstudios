#!/usr/bin/env python3
"""Ponte entre o CRM e as tags de cor do Finder — roda NO MAC (usa xattr do macOS).

O princípio (docs/18): a tag nunca é a fonte de verdade — ela é interface. Este script mantém
os dois lados coerentes:

  refletir   CRM → Finder: pinta cada pasta de projeto com a cor da fase registrada no banco.
  capturar   Finder → CRM: lê as tags que o editor mudou na mão e registra a transição no CRM.

Uso (no Mac):
  export DUCK_URL=https://crm.duckstudios.com.br DUCK_USUARIO=duck DUCK_SENHA=...
  export DUCK_PASTA="/Volumes/RAID/DuckStudios_Projetos"
  python3 refletir_tags.py refletir
  python3 refletir_tags.py capturar

Agendar (launchd ou cron do Mac) a cada 5 min nos dois sentidos e o Finder vira um painel:
o editor muda a cor da pasta → o CRM sabe; alguém muda a fase no CRM → a pasta muda de cor.
"""
import base64
import json
import os
import plistlib
import subprocess
import sys
import urllib.request

URL = os.environ.get("DUCK_URL", "").rstrip("/")
PASTA = os.environ.get("DUCK_PASTA", "")
XATTR_TAGS = "com.apple.metadata:_kMDItemUserTags"

# nome da tag no Finder + índice de cor do macOS
CORES = {"Red": 6, "Yellow": 5, "Green": 2, "Purple": 3}
FINDER_PARA_ESTADO = {"Red": "ingerido", "Yellow": "em_edicao",
                      "Green": "aprovado", "Purple": "entregue"}


def api(caminho, dados=None):
    req = urllib.request.Request(URL + caminho,
                                 data=json.dumps(dados).encode() if dados else None,
                                 headers={"Content-Type": "application/json"})
    cred = f"{os.environ.get('DUCK_USUARIO', 'duck')}:{os.environ['DUCK_SENHA']}"
    req.add_header("Authorization", "Basic " + base64.b64encode(cred.encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def ler_tags(pasta):
    r = subprocess.run(["xattr", "-p", "-x", XATTR_TAGS, pasta],
                       capture_output=True, text=True)
    if r.returncode:
        return []
    binario = bytes.fromhex(r.stdout.replace(" ", "").replace("\n", ""))
    return plistlib.loads(binario)


def gravar_tag(pasta, cor_finder):
    valor = plistlib.dumps([f"{cor_finder}\n{CORES[cor_finder]}"], fmt=plistlib.FMT_BINARY)
    subprocess.run(["xattr", "-w", "-x", XATTR_TAGS, valor.hex(), pasta], check=True)


def pasta_do(slug):
    """A pasta do projeto é a que tem o slug no nome (o Finder real usa nomes livres tipo
    '16 AGOSTO - ZH'; o vínculo é feito por 'pasta_raiz' no CRM ou pelo slug)."""
    for raiz, dirs, _ in os.walk(PASTA):
        for d in dirs:
            if slug in d.lower().replace(" ", "-"):
                return os.path.join(raiz, d)
        dirs[:] = [d for d in dirs if not d.startswith(".")]
    return None


def refletir():
    for p in api("/api/projetos"):
        pasta = p.get("pasta_raiz") or pasta_do(p["slug"])
        if not pasta or not os.path.isdir(pasta):
            print(f"  ? {p['slug']}: pasta não encontrada")
            continue
        gravar_tag(pasta, p["finder"])
        print(f"  ✓ {p['slug']} → {p['finder']}")


def capturar():
    for p in api("/api/projetos"):
        pasta = p.get("pasta_raiz") or pasta_do(p["slug"])
        if not pasta or not os.path.isdir(pasta):
            continue
        tags = [t.split("\n")[0] for t in ler_tags(pasta)]
        estado_tag = next((FINDER_PARA_ESTADO[t] for t in tags
                           if t in FINDER_PARA_ESTADO), None)
        if estado_tag and estado_tag != p["estado_editorial"]:
            r = api(f"/api/projetos/{p['slug']}/estado", {"estado": estado_tag})
            print(f"  ✓ {p['slug']}: {p['estado_editorial']} → {estado_tag} ({r['ok']})")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("refletir", "capturar"):
        sys.exit(__doc__)
    if not URL or not PASTA or not os.environ.get("DUCK_SENHA"):
        sys.exit("defina DUCK_URL, DUCK_SENHA e DUCK_PASTA")
    {"refletir": refletir, "capturar": capturar}[sys.argv[1]]()
