FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential pkg-config default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 ojasvirudraksha \
    && mkdir -p /data /app/.local /app/media \
    && chown -R ojasvirudraksha:ojasvirudraksha /data /app

COPY --chown=ojasvirudraksha:ojasvirudraksha . .
RUN chmod +x /app/docker/entrypoint.sh

USER ojasvirudraksha
EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
