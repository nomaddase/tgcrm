# Telegram CRM Bot with AI Assistant

This repository contains the source code for a Telegram-based CRM system that leverages AI to assist sales managers. The bot streamlines client management, automates reminders, parses invoices, and integrates with OpenAI to support communication workflows.

## Features
- **Client onboarding** based on phone number lookup with automatic deal creation.
- **Deal management** via inline keyboards and quick actions for invoices, reminders, and status updates.
- **PDF invoice processing** using PyMuPDF + Tesseract OCR with automatic extraction of totals and line items.
- **AI-assisted consultations** leveraging OpenAI to help managers answer product-specific questions.
- **Interaction logging** with AI-generated coaching tips before storing manager summaries.
- **Reminder scheduling** via Celery workers and proactive follow-up rules that respect working hours.
- **Supervisor tools** for aggregated reporting and secure settings management.

## Project Structure
```
.
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── src/
│   └── tgcrm/
│       ├── bot/
│       │   ├── bot_factory.py
│       │   ├── handlers/
│       │   │   ├── __init__.py
│       │   │   ├── settings.py
│       │   │   └── start.py
│       │   └── main.py
│       ├── config.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── session.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── ai.py
│       │   ├── deals.py
│       │   └── pdf_processing.py
│       └── tasks/
│           ├── __init__.py
│           ├── celery_app.py
│           └── reminders.py
└── tests/
```

The `tests/` directory is reserved for automated tests.

## Getting Started

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and replace placeholder values:

```bash
cp .env.example .env
```

Update sensitive information such as the Telegram bot token, OpenAI API key, and database credentials.

### 2. Local Development

Install dependencies and run the bot locally:

```bash
pip install -e .[dev]
python -m tgcrm.bot.main
```

To initialize the database schema during development you can run:

```python
import asyncio
from tgcrm.db.session import init_models
asyncio.run(init_models())
```

### 3. Running with Docker Compose

```bash
docker compose up --build
```

The stack includes:
- **bot** – aiogram polling worker.
- **worker** – Celery worker for background jobs.
- **beat** – Celery beat scheduler for periodic tasks.
- **postgres** – PostgreSQL 15 with persistent volume.
- **redis** – Redis 7 used as Celery broker and backend.

### 4. Background Jobs

Celery tasks are defined in `tgcrm.tasks`. The `beat` service can be configured with periodic schedules for:
- `send_due_reminders` – sends scheduled reminders to managers.
- `proactive_follow_up` – checks deals lacking recent interactions and notifies managers during working hours.

### 5. Invoice Processing

`tgcrm.services.pdf_processing` provides utilities for extracting totals and line items from PDF invoices. The extracted data is stored through the `attach_invoice` service, which also updates deal status and amount.

### 6. AI Integration

`tgcrm.services.ai` wraps the OpenAI client and exposes helper functions for generating advice, summarizing interactions, and answering product-specific questions. Configure the API key via the `OPENAI_API_KEY` environment variable.

## Deployment

The provided Dockerfile and Compose configuration are suitable for containerized deployments. To automate delivery you can implement a GitHub Actions workflow that:
1. Builds and pushes the Docker image.
2. Connects to the target server via SSH.
3. Updates the `docker-compose.yml` file if required.
4. Pulls the latest image and restarts the stack with `docker compose up -d`.

## License

This project is released under the MIT License.
