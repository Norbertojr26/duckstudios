#!/usr/bin/env python3
"""duck_mac — o runtime local. Roda no Mac Mini; é gerenciado inteiro pelo CRM.

Modelo de segurança:
  * a máquina LIGA para o CRM (HTTPS + Basic auth) — nenhuma porta aberta no Mac;
  * ela só toca no que estiver na lista de pastas autorizadas, que vem do CRM a cada
    heartbeat — revogar acesso é um clique na tela /maquinas, sem tocar no Mac;
  * o conjunto de tarefas é fechado (inventariar, refletir/capturar tags); nada de
    comando arbitrário vindo da rede.

Uso:
  export DUCK_URL=https://crm.duckstudios.com.br DUCK_USUARIO=duck DUCK_SENHA=••• \\
         DUCK_MAQUINA="mac-mini-studio"
  python3 duck_mac.py            # laço: heartbeat + tarefas a cada 20s
  python3 duck_mac.py --uma-vez  # uma passada (teste)
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

URL = os.environ.get("DUCK_URL", "").rstrip("/")
MAQUINA = os.environ.get("DUCK_MAQUINA", "mac-mini")
INTERVALO = int(os.environ.get("DUCK_INTERVALO", "20"))


def api(caminho, dados=None):
    req = urllib.request.Request(URL + caminho,
                                 data=json.dumps(dados).encode() if dados is not None else None,
                                 headers={"Content-Type": "application/json"})
    cred = f"{os.environ.get('DUCK_USUARIO', 'duck')}:{os.environ['DUCK_SENHA']}"
    req.add_header("Authorization", "Basic " + base64.b64encode(cred.encode()).decode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def dentro_de(caminho, pastas):
    caminho = os.path.realpath(caminho)
    return any(caminho == p or caminho.startswith(p + os.sep)
               for p in (os.path.realpath(x["caminho"]) for x in pastas))


def info_local():
    info = {"plataforma": sys.platform, "runtime": "duck_mac v1"}
    try:
        uso = shutil.disk_usage("/")
        info["disco_livre_gb"] = round(uso.free / 1e9)
    except OSError:
        pass
    if os.path.isdir("/Volumes"):
        info["volumes"] = sorted(d for d in os.listdir("/Volumes") if not d.startswith("."))
    return info


# ------------------------------------------------------------------- tarefas

def t_inventariar_pastas(pastas, _payload):
    """Cliente/Job dois níveis abaixo de cada pasta autorizada — o retrato que o CRM mostra."""
    arvore = []
    for p in pastas:
        raiz = p["caminho"]
        if not os.path.isdir(raiz):
            arvore.append({"pasta": raiz, "erro": "não montada"})
            continue
        clientes = []
        for c in sorted(os.listdir(raiz)):
            cheio = os.path.join(raiz, c)
            if c.startswith(".") or not os.path.isdir(cheio):
                continue
            jobs = sorted(j for j in os.listdir(cheio)
                          if os.path.isdir(os.path.join(cheio, j)) and not j.startswith("."))
            clientes.append({"cliente": c, "jobs": jobs[:40]})
        arvore.append({"pasta": raiz, "clientes": clientes[:60]})
    return {"arvore": arvore}


def _refletor(modo, pastas):
    """Reusa o refletir_tags.py com a primeira pasta autorizada como raiz de busca."""
    graváveis = [p for p in pastas if p["permissao"] == "leitura_escrita"]
    alvo = (graváveis if modo == "refletir" else pastas)
    if not alvo:
        return {"erro": "nenhuma pasta autorizada" +
                        (" com escrita (tags exigem ler+escrever)" if modo == "refletir" else "")}
    env = {**os.environ, "DUCK_PASTA": alvo[0]["caminho"]}
    r = subprocess.run([sys.executable,
                        os.path.join(os.path.dirname(__file__), "refletir_tags.py"), modo],
                       capture_output=True, text=True, env=env, timeout=300)
    return {"saida": (r.stdout + r.stderr)[-1500:], "codigo": r.returncode}


def t_refletir_tags(pastas, _p):
    return _refletor("refletir", pastas)


def t_capturar_tags(pastas, _p):
    return _refletor("capturar", pastas)


TAREFAS = {"inventariar_pastas": t_inventariar_pastas,
           "refletir_tags": t_refletir_tags,
           "capturar_tags": t_capturar_tags}


def passada():
    hb = api("/api/mac/heartbeat", {"maquina": MAQUINA, "info": info_local()})
    pastas = hb.get("pastas", [])
    t = api(f"/api/mac/proxima-tarefa?maquina={urllib.request.quote(MAQUINA)}")["tarefa"]
    if not t:
        return False
    print(f"→ tarefa {t['tipo']} (#{t['id']})")
    try:
        fn = TAREFAS.get(t["tipo"])
        if not fn:
            raise ValueError(f"tarefa desconhecida: {t['tipo']}")
        resultado = fn(pastas, t.get("payload") or {})
        api(f"/api/mac/resultado/{t['id']}",
            {"ok": "erro" not in resultado, "tipo": t["tipo"], "resultado": resultado,
             "erro": resultado.get("erro")})
        print(f"  ✓ {json.dumps(resultado, ensure_ascii=False)[:160]}")
    except Exception as e:                                            # noqa: BLE001
        api(f"/api/mac/resultado/{t['id']}",
            {"ok": False, "tipo": t["tipo"], "erro": f"{type(e).__name__}: {e}"})
        print(f"  ✕ {e}")
    return True


if __name__ == "__main__":
    if not URL or not os.environ.get("DUCK_SENHA"):
        sys.exit("defina DUCK_URL e DUCK_SENHA (e DUCK_MAQUINA)")
    if "--uma-vez" in sys.argv:
        while passada():
            pass
        sys.exit(0)
    print(f"duck_mac '{MAQUINA}' → {URL} (a cada {INTERVALO}s)")
    while True:
        try:
            passada()
        except Exception as e:                                        # noqa: BLE001
            print(f"! {type(e).__name__}: {e} — tentando de novo em {INTERVALO}s")
        time.sleep(INTERVALO)
