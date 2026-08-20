FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/    ./app/
COPY db/     ./db/
COPY design/ ./design/

# A identidade vira estático da aplicação: uma fonte de verdade visual, sem cópia.
RUN cp design/tokens.css app/static/ && cp -r design/logo app/static/logo && \
    (cp -r design/fonts app/static/fonts 2>/dev/null || true)

EXPOSE 8000
# Railway define $PORT; o padrão cobre execução local.
CMD ["sh", "-c", "python -m app.migrar && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
