FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential tesseract-ocr libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY entrypoint.sh /app/entrypoint.sh
COPY src /app/src

RUN chmod +x /app/entrypoint.sh

RUN pip install --upgrade pip \
    && pip install -e .[dev]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "tgcrm.bot.main"]
