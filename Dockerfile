# ==========================
# tgcrm — финальная версия Dockerfile
# ==========================
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем код проекта
COPY . /app

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir \
    aiogram==3.* \
    SQLAlchemy==2.* \
    asyncpg==0.* \
    psycopg2-binary==2.* \
    redis==5.* \
    celery==5.* \
    python-dotenv==1.* \
    pydantic==2.* \
    pydantic-settings==2.* \
    PyMuPDF==1.* \
    openai==1.* \
    tenacity==8.* \
    aiofiles==23.* \
    requests==2.* \
    pytesseract==0.* \
    && pip cache purge

# Устанавливаем переменную окружения для Python
ENV PYTHONPATH=/app/src

# Команда по умолчанию
CMD ["python", "manage.py"]
