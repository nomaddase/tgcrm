#!/usr/bin/env python3
import asyncio
import sys
import time
from dotenv import load_dotenv
from tgcrm.db.session import init_models

load_dotenv()

async def init_db():
    print("🔄 Инициализация базы данных...")
    retries = 5
    for attempt in range(1, retries + 1):
        try:
            await init_models()
            print("✅ База данных успешно инициализирована.")
            return
        except Exception as e:
            print(f"⚠️  Попытка {attempt}/{retries} не удалась: {e}")
            if attempt < retries:
                time.sleep(3)
            else:
                print("❌ Не удалось подключиться к базе данных. Проверь настройки .env и соединение.")
                sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Использование: python manage.py init-db")
        sys.exit(1)

    command = sys.argv[1]
    if command == "init-db":
        asyncio.run(init_db())
    else:
        print(f"Неизвестная команда: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
