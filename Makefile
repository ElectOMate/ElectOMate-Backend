.PHONY: help dev dev-logs dev-shell db-migrate migration prod prod-logs prod-shell prod-migrate publish down clean

# Default target
help:
	@echo "Available commands:"
	@echo "  dev              - Start full development stack with Docker Compose"
	@echo "  dev-logs         - View development application logs"
	@echo "  dev-shell        - Access development container shell"
	@echo "  db-migrate       - Run database migrations in development container"
	@echo "  migration        - Create new migration (use: make migration message='your message')"
	@echo "  prod             - Start production stack (requires external database)"
	@echo "  prod-logs        - View production application logs"
	@echo "  prod-shell       - Access production container shell"
	@echo "  prod-migrate     - Run database migrations in production container"
	@echo "  down             - Stop all services"
	@echo "  clean            - Clean up all containers and volumes"

# Start full development stack with Docker Compose
dev:
	docker compose watch
	@echo "Development stack started!"
	@echo "Application: http://localhost:8000"
	@echo "Database: localhost:5433"

# View development application logs
dev-logs:
	docker compose logs -f app

# Access development container shell
dev-shell:
	docker compose exec app bash

# Run database migrations in development container
db-migrate:
	docker compose exec app alembic upgrade head

# Create new migration (usage: make migration message="your message")
migration:
	@if [ -z "$(message)" ]; then \
		echo "Error: Please provide a message. Usage: make migration message='your message'"; \
		exit 1; \
	fi
	docker compose exec app alembic revision --autogenerate -m "$(message)"

# Start production stack (requires external database configuration)
prod:
	@echo "Checking for required environment variables..."
	@if [ -z "$$POSTGRES_HOST" ]; then \
		echo "Error: POSTGRES_HOST is required for production deployment."; \
		echo "Please set the following environment variables in your .env file:"; \
		echo "  POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB"; \
		exit 1; \
	fi
	docker compose -f docker-compose.prod.yml up --build -d
	@echo "Production application started at http://localhost:8000"
	@echo "Using external PostgreSQL database at $$POSTGRES_HOST"

# View production application logs
prod-logs:
	docker compose -f docker-compose.prod.yml logs -f app

# Access production container shell
prod-shell:
	docker compose -f docker-compose.prod.yml exec app bash

# Run database migrations in production container
prod-migrate:
	docker compose -f docker-compose.prod.yml exec app alembic upgrade head

publish:
	az acr run -f ./acr-build-task.yml --registry embackendacr --set image="em/backend:latest" .

# Stop all services
down:
	docker compose down
	docker compose -f docker-compose.prod.yml down

# Clean up all containers and volumes
clean:
	docker compose down -v --remove-orphans
	docker compose -f docker-compose.prod.yml down -v --remove-orphans
	docker system prune -f
