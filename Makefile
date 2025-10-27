.PHONY: build up down logs init-db deploy

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down --remove-orphans

logs:
	docker compose logs -f

init-db:
	docker compose run --rm bot python manage.py init-db

deploy:
	docker compose down --remove-orphans
	docker compose pull
	docker compose up -d
	docker compose logs -f
