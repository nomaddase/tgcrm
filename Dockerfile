FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем проект
COPY pyproject.toml poetry.lock* ./
COPY src /app/src
COPY manage.py /app/manage.py

ENV PYTHONPATH=/app/src

# Устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry install --no-root --only main

CMD ["python", "-m", "tgcrm.bot.main"]
