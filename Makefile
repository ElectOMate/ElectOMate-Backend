.PHONY: help install db-start db-migrate dev migration docker-build docker-run clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install     - Install dependencies using uv"
	@echo "  db-start    - Start PostgreSQL database in Docker"
	@echo "  db-migrate  - Run database migrations"
	@echo "  dev         - Start development server"
	@echo "  migration   - Create new migration (use: make migration message='your message')"
	@echo "  docker-build - Build Docker container"
	@echo "  docker-run  - Run Docker container"
	@echo "  clean       - Clean up Docker containers and volumes"

# Install dependencies
install:
	uv sync

# Start PostgreSQL database in Docker
db-start:
	docker run -d \
		--name em_postgres \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_DB=em \
		-p 5432:5432 \
		-v pgdata:/var/lib/postgresql/data \
		postgres

# Run database migrations
db-migrate:
	uv run alembic upgrade head

# Start development server
dev:
	uv run --dev --env-file .env fastapi dev src/em_backend/main.py

# Create new migration (usage: make migration message="your message")
migration:
	@if [ -z "$(message)" ]; then \
		echo "Error: Please provide a message. Usage: make migration message='your message'"; \
		exit 1; \
	fi
	uv run alembic revision --autogenerate -m "$(message)"

# Build Docker container
docker-build:
	docker build -t em/backend .

# Run Docker container
docker-run:
	docker run --env-file ./.env -p 8000:8000 em/backend

# Clean up Docker containers and volumes
clean:
	-docker stop em_postgres
	-docker rm em_postgres
	-docker volume rm pgdata