#!/usr/bin/env python3
"""duck_ingest — offload verificado de cartão, o núcleo do agente DIT. Roda no Mac Mini.

O que faz, na ordem do SOP-001:
  1. inventaria a origem (nunca escreve nela);
  2. copia para ≥2 destinos, cada um lido DA ORIGEM (destino1→destino2 propagaria erro de leitura);
  3. verifica hash de cada arquivo relendo o destino; refaz o que divergir;
  4. grava manifesto e relatório em _INGEST/ de cada destino;
  5. registra tudo no CRM, que abre a aprovação "liberar cartão para formatação" — formatar
     continua sendo gesto HUMANO, na câmera.

Idempotente: reexecutar pula o que já está verificado (manifesto), completa o que falta.
Proxies ficam fora de propósito — o editor não usa (docs/19).

Uso:
  python3 duck_ingest.py --origem /Volumes/SD_A --camera FX3 --projeto 16-agosto-zh \\
      --destino "/Volumes/RAID/Zé Humberto/16 AGOSTO - ZH" --destino /Volumes/SHUTTLE/backup
  (destinos: o 1º é a pasta do JOB — o material entra em VIDEOS/{CAMERA}/CARD_NN/;
   os demais são backups espelhando o mesmo caminho relativo)

Hash: xxHash64 se o pacote `xxhash` estiver instalado (pip3 install xxhash); senão BLAKE2b,
com o algoritmo anotado no manifesto — verificação sempre compara igual com igual.
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import time
import urllib.request
import uuid as uuid_mod

try:
    import xxhash
    ALGO = "xxh64"
    def _h(): return xxhash.xxh64()
except ImportError:
    ALGO = "blake2b"
    def _h(): return hashlib.blake2b(digest_size=8)

BLOCO = 8 * 1024 * 1024
IGNORAR = {".DS_Store", ".Spotlight-V100", ".fseventsd", ".Trashes"}


def hash_arquivo(caminho):
    h = _h()
    with open(caminho, "rb") as f:
        while True:
            b = f.read(BLOCO)
            if not b:
                return h.hexdigest()
            h.update(b)


def inventariar(origem):
    itens = []
    for raiz, dirs, arquivos in os.walk(origem):
        dirs[:] = [d for d in dirs if d not in IGNORAR]
        for a in arquivos:
            if a in IGNORAR or a.startswith("._"):
                continue
            cheio = os.path.join(raiz, a)
            itens.append({"rel": os.path.relpath(cheio, origem),
                          "bytes": os.path.getsize(cheio)})
    return sorted(itens, key=lambda i: i["rel"])


def copiar_verificando(origem_arq, destino_arq, hash_origem):
    os.makedirs(os.path.dirname(destino_arq), exist_ok=True)
    tmp = destino_arq + ".part"
    with open(origem_arq, "rb") as o, open(tmp, "wb") as d:
        while True:
            b = o.read(BLOCO)
            if not b:
                break
            d.write(b)
        d.flush()
        os.fsync(d.fileno())
    if hash_arquivo(tmp) != hash_origem:
        os.remove(tmp)
        return False
    os.replace(tmp, destino_arq)
    return True


def proximo_card(pasta_camera):
    n = 1
    while os.path.isdir(os.path.join(pasta_camera, f"CARD_{n:02d}")):
        n += 1
    return f"CARD_{n:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--origem", required=True)
    ap.add_argument("--camera", required=True)
    ap.add_argument("--projeto", required=True, help="slug do projeto no CRM")
    ap.add_argument("--destino", action="append", required=True,
                    help="1º = pasta do JOB; repita para cada backup (mínimo 2 no total)")
    ap.add_argument("--card", help="reusar um CARD_NN existente (retomada)")
    ap.add_argument("--sem-crm", action="store_true", help="offline: registra depois")
    ap.add_argument("--reverificar", action="store_true",
                    help="reler e re-hashear TODO destino (caça bitrot; lento em TBs)")
    a = ap.parse_args()

    origem = os.path.abspath(a.origem)
    if len(a.destino) < 2:
        sys.exit("ERRO: são necessários ≥2 destinos — uma cópia não é backup (SOP-001).")
    for d in a.destino:
        if os.path.abspath(d).startswith(origem):
            sys.exit("ERRO: destino dentro da origem — nunca se escreve no cartão.")

    print(f"→ inventariando {origem} …")
    itens = inventariar(origem)
    total = sum(i["bytes"] for i in itens)
    print(f"  {len(itens)} arquivos · {total/1e9:.2f} GB · hash {ALGO}")
    if not itens:
        sys.exit("origem vazia — nada a fazer")

    job = os.path.abspath(a.destino[0])
    camera_dir = os.path.join(job, "VIDEOS", a.camera.upper())
    card = a.card or proximo_card(camera_dir)
    rel_base = os.path.join("VIDEOS", a.camera.upper(), card)
    card_uuid = f"{a.camera.upper()}-{card}-{uuid_mod.uuid5(uuid_mod.NAMESPACE_URL, origem + str(total))}"

    print(f"→ hasheando a origem …")
    for i in itens:
        i["hash"] = hash_arquivo(os.path.join(origem, i["rel"]))

    divergencias = []
    destinos_ok = []
    for destino in a.destino:
        base = os.path.join(os.path.abspath(destino), rel_base) \
            if os.path.abspath(destino) != job else os.path.join(camera_dir, card)
        ingest_dir = os.path.join(base, "_INGEST")
        os.makedirs(ingest_dir, exist_ok=True)
        manifesto_arq = os.path.join(ingest_dir, "manifesto.json")
        prontos = {}
        if os.path.exists(manifesto_arq):
            prontos = {m["rel"]: m["hash"] for m in json.load(open(manifesto_arq))["arquivos"]}

        print(f"→ destino {base}")
        copiados = pulados = 0
        for i in itens:
            alvo = os.path.join(base, i["rel"])
            # manifesto diz verificado + tamanho bate = pula. Tamanho é a checagem barata que
            # pega truncamento/corrupção grosseira; --reverificar refaz o hash inteiro.
            intacto = (prontos.get(i["rel"]) == i["hash"] and os.path.exists(alvo)
                       and os.path.getsize(alvo) == i["bytes"])
            if intacto and a.reverificar:
                intacto = hash_arquivo(alvo) == i["hash"]
                if not intacto:
                    print(f"  ! bitrot detectado em {i['rel']} — recopiando")
            if intacto:
                pulados += 1
                continue
            ok = False
            for tentativa in (1, 2):
                if copiar_verificando(os.path.join(origem, i["rel"]), alvo, i["hash"]):
                    ok = True
                    break
                print(f"  ! hash divergiu em {i['rel']} (tentativa {tentativa})")
            if ok:
                copiados += 1
            else:
                divergencias.append({"rel": i["rel"], "destino": base})

        json.dump({"algoritmo": ALGO, "card_uuid": card_uuid, "origem": origem,
                   "gerado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "arquivos": [{"rel": i["rel"], "bytes": i["bytes"], "hash": i["hash"]}
                                for i in itens]},
                  open(manifesto_arq, "w"), ensure_ascii=False, indent=1)
        print(f"  ✓ {copiados} copiados · {pulados} já verificados · manifesto gravado")
        destinos_ok.append(base)

    status = "verificado" if not divergencias else "parcial"
    relatorio = {"card_uuid": card_uuid, "projeto": a.projeto, "camera": a.camera.upper(),
                 "card": card, "arquivos": len(itens), "bytes": total, "algoritmo": ALGO,
                 "destinos": destinos_ok, "divergencias": divergencias, "status": status}
    for base in destinos_ok:
        json.dump(relatorio, open(os.path.join(base, "_INGEST", "relatorio.json"), "w"),
                  ensure_ascii=False, indent=1)

    if a.sem_crm:
        print(f"⚠ offline: registre depois com o relatorio.json — status {status}")
    else:
        url = os.environ["DUCK_URL"].rstrip("/") + "/api/agentes/dit/offload"
        cred = f"{os.environ.get('DUCK_USUARIO', 'duck')}:{os.environ['DUCK_SENHA']}"
        req = urllib.request.Request(url, data=json.dumps({
            **relatorio,
            "arquivos_detalhe": [{"rel": os.path.join(rel_base, i["rel"]),
                                  "nome": os.path.basename(i["rel"]),
                                  "bytes": i["bytes"], "hash": i["hash"]} for i in itens],
        }).encode(), headers={"Content-Type": "application/json",
                              "Authorization": "Basic " +
                              base64.b64encode(cred.encode()).decode()})
        with urllib.request.urlopen(req, timeout=60) as r:
            print("→ CRM:", json.loads(r.read()))

    if status == "verificado":
        print(f"\n✓ {len(itens)} arquivos verificados em {len(destinos_ok)} destinos.")
        print("  O cartão SÓ deve ser formatado após aprovação no CRM — e por você, na câmera.")
    else:
        print(f"\n⚠ CONCLUÍDO COM DIVERGÊNCIAS ({len(divergencias)}). NÃO formate o cartão.")
        sys.exit(2)


if __name__ == "__main__":
    main()
