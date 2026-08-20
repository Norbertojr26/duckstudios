# Deploy no Railway

O build falhou na primeira tentativa porque o repositório só tinha documentos, SQL e mocos
estáticos — não havia aplicação. Agora há. Este documento é o passo a passo.

> **Railway é para testar e ver funcionando.** A operação em locação continua sendo local no
> Mac Mini: a Starlink cai, e conferência de equipamento não pode depender de nuvem. O plano
> segue o de [`02-arquitetura.md`](02-arquitetura.md) — o mesmo container roda nos dois lugares.

---

## 1. Postgres

No projeto do Railway: **New → Database → PostgreSQL**.

Depois, no serviço `duckstudios` → **Variables**, adicione a referência:

```
DATABASE_URL = ${{Postgres.DATABASE_URL}}
```

Sem essa variável a aplicação sobe e o healthcheck falha — ela não inventa banco.

## 2. Senha (não pule)

```
APP_SENHA = <uma senha forte>
APP_USUARIO = duck          # opcional, esse é o padrão
```

Sem `APP_SENHA` a aplicação **serve mesmo assim**, mas mostra um aviso vermelho em todas as telas:
uma URL pública do Railway sem senha expõe seu inventário de meio milhão, os valores e os clientes.
`/healthz` e os arquivos estáticos ficam livres — o resto, inclusive a API, exige a senha.

## 3. Domínio

O serviço nasce como *Unexposed*. **Settings → Networking → Generate Domain.**

## 4. Deploy

O `railway.json` já aponta para o `Dockerfile` e configura o healthcheck em `/healthz`.
Cada push na branch dispara build.

Na subida, o container roda `python -m app.migrar` antes do servidor:

- cria o schema **se ainda não existir**
- aplica as cargas, que são idempotentes
- resultado: o ambiente sobe com **os 156 itens reais**, os 14 sublocados, os 10 kits e a tabela
  de preços — não é um banco vazio para você preencher de novo

## 5. Conferir

| Endereço | O que é |
|---|---|
| `/` | painel — o que está fora, atrasos, patrimônio |
| `/equipamento` | busca por nome, código, marca; filtro por categoria e por próprio/sublocado |
| `/saidas` | histórico |
| `/saidas/{id}` | conferência com scan, saída e retorno |
| `/api/docs` | **a API que os agentes vão usar** |

Teste o caminho todo em um minuto: no painel, escreva um nome em *Quem leva* → **Nova saída** →
bipe `0118` (Sony FX6) → troque para **Conferir retorno** → bipe `0118` → **Encerrar saída**.

### O que deve falhar, e falha

Vale testar, porque é onde o sistema protege você de si mesmo e do agente:

| Tentativa | Resultado |
|---|---|
| Bipar `CAT-01` (GoPro sublocada) numa saída | recusa: *"é sublocado, cote com o fornecedor antes"* |
| Bipar um código que não existe | recusa |
| Bipar `0118` numa **segunda** saída no mesmo período | recusa — **a constraint do banco**, não a tela |
| Encerrar com item pendente | recusa e diz quantos faltam |

O terceiro é o mais importante: o `EXCLUDE USING gist` torna o overbooking impossível mesmo que a
aplicação (ou um agente) tenha um bug.

## 6. Variáveis

| Variável | Obrigatória | Para quê |
|---|---|---|
| `DATABASE_URL` | sim | Postgres (referência ao serviço) |
| `APP_SENHA` | na prática sim | Basic auth |
| `APP_USUARIO` | não | padrão `duck` |
| `PORT` | não | o Railway injeta |

## 7. Rodar igual, localmente

```bash
createdb duck
export DATABASE_URL=postgresql:///duck
pip install -r requirements.txt
python -m app.migrar
uvicorn app.main:app --reload
```

Ou pelo Docker, exatamente a imagem que o Railway constrói:

```bash
docker build -t duck .
docker run -p 8000:8000 -e DATABASE_URL=... -e APP_SENHA=... duck
```

## O que ainda não está aqui

Deliberadamente fora deste primeiro corte, para ele subir hoje:

- **Offline** — o app ainda exige rede. É o próximo passo e é o que decide o uso em locação
- **Câmera do celular** como scanner (hoje o campo aceita leitor USB e digitação)
- Termo de responsabilidade em PDF com assinatura
- Fotos de estado na saída e no retorno
- Login por usuário (Basic auth é senha única, não identifica quem conferiu)
