#!/usr/bin/env python3
"""duck_mac — o runtime local. Roda no Mac Mini; é gerenciado inteiro pelo CRM.

Modelo de segurança:
  * a máquina LIGA para o CRM (HTTPS + Basic auth) — nenhuma porta aberta no Mac;
  * ela só toca no que estiver na lista de pastas autorizadas, que vem do CRM a cada
    heartbeat — revogar acesso é um clique na tela /maquinas, sem tocar no Mac;
  * o conjunto de tarefas é fechado (inventariar, tags, criar job, mover, lixeira);
    nada de comando arbitrário vindo da rede;
  * escrita exige pasta autorizada como "ler+escrever", e NADA é apagado: o máximo
    destrutivo é mover para _LIXEIRA/ dentro da própria pasta — reversível no Finder.

Uso:
  export DUCK_URL=https://crm.duckstudios.com.br DUCK_USUARIO=duck DUCK_SENHA=••• \\
         DUCK_MAQUINA="mac-mini-studio"
  python3 duck_mac.py            # laço: heartbeat + tarefas a cada 20s
  python3 duck_mac.py --uma-vez  # uma passada (teste)
"""
import base64
import datetime
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


# --- tarefas que ESCREVEM — toda validação antes de tocar o disco ---

def _raiz_de(caminho, pastas, escrita=False):
    """A pasta autorizada que contém o caminho — ou ValueError. É a única porta de entrada
    das tarefas de escrita; realpath primeiro, para symlink não furar a cerca."""
    real = os.path.realpath(caminho)
    for p in pastas:
        raiz = os.path.realpath(p["caminho"])
        if real == raiz or real.startswith(raiz + os.sep):
            if escrita and p["permissao"] != "leitura_escrita":
                raise ValueError(f"pasta autorizada só para leitura: {p['caminho']}")
            return real, raiz
    raise ValueError(f"fora das pastas autorizadas: {caminho}")


MODELO_JOB = ("ASSETS", "AUDIOS/SFX", "AUDIOS/GRAVADOR", "AUDIOS/MUSICAS", "SEQ", "VIDEOS")


def t_criar_job(pastas, p):
    """CLIENTE/JOB com o esqueleto real (docs/19): ASSETS, AUDIOS/*, SEQ, VIDEOS."""
    cliente, job = (p.get("cliente") or "").strip(), (p.get("job") or "").strip()
    if not cliente or not job:
        return {"erro": "faltou cliente e/ou job"}
    if any(ch in cliente + job for ch in ("/", "\\", "..")):
        return {"erro": "cliente/job são nomes, não caminhos"}
    grav = [x for x in pastas if x["permissao"] == "leitura_escrita"]
    if not grav:
        return {"erro": "nenhuma pasta autorizada com escrita"}
    base, _ = _raiz_de(os.path.join(p.get("raiz") or grav[0]["caminho"], cliente, job),
                       pastas, escrita=True)
    criadas = []
    for sub in MODELO_JOB:
        alvo = os.path.join(base, sub)
        if not os.path.isdir(alvo):
            os.makedirs(alvo)
            criadas.append(sub)
    return {"job": base, "criadas": criadas or ["nada — estrutura já existia"]}


def t_mover(pastas, p):
    """Mover/renomear arquivo ou pasta. Nunca sobrescreve; serve também para restaurar
    algo da _LIXEIRA (é só apontar a origem para lá)."""
    origem, _ = _raiz_de(p.get("origem") or "", pastas, escrita=True)
    destino, _ = _raiz_de(p.get("destino") or "", pastas, escrita=True)
    if not os.path.exists(origem):
        return {"erro": f"origem não existe: {origem}"}
    if os.path.exists(destino):
        return {"erro": f"destino já existe — não sobrescrevo: {destino}"}
    if origem == destino or destino.startswith(origem + os.sep):
        return {"erro": "destino dentro da própria origem"}
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.move(origem, destino)
    return {"movido": {"de": origem, "para": destino}}


def t_enviar_lixeira(pastas, p):
    """O único 'apagar' que existe: mover para _LIXEIRA/AAAA-MM-DD/ na raiz autorizada.
    rm não existe neste runtime — esvaziar a lixeira é decisão humana, no Finder."""
    real, raiz = _raiz_de(p.get("caminho") or "", pastas, escrita=True)
    if real == raiz:
        return {"erro": "não mando uma pasta autorizada inteira para a lixeira"}
    if not os.path.exists(real):
        return {"erro": f"não existe: {real}"}
    if "_LIXEIRA" in real.split(os.sep):
        return {"erro": "já está na lixeira"}
    pasta = os.path.join(raiz, "_LIXEIRA", datetime.date.today().isoformat())
    os.makedirs(pasta, exist_ok=True)
    destino = os.path.join(pasta, os.path.basename(real))
    n = 1
    while os.path.exists(destino):
        destino = os.path.join(pasta, f"{os.path.basename(real)}_{n}")
        n += 1
    shutil.move(real, destino)
    return {"lixeira": destino, "aviso": "nada foi apagado — restaurar é mover de volta"}


TAREFAS = {"inventariar_pastas": t_inventariar_pastas,
           "refletir_tags": t_refletir_tags,
           "capturar_tags": t_capturar_tags,
           "criar_job": t_criar_job,
           "mover": t_mover,
           "enviar_lixeira": t_enviar_lixeira}


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
