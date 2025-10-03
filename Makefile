.PHONY: help dev dev-logs dev-shell db-migrate migration load-chile-data prod-deploy prod-logs prod-shell down clean

# Default target
help:
	@echo "Available commands:"
	@echo "  dev              - Start full development stack with Docker Compose"
	@echo "  dev-logs         - View development application logs"
	@echo "  dev-shell        - Access development container shell"
	@echo "  db-migrate       - Run database migrations in development container"
	@echo "  migration        - Create new migration (use: make migration message='your message')"
	@echo "  load-chile-data  - Load Chile election data into the database"
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

# Load Chile election data (starts services and runs data loading script)
load-chile-data:
	@echo "Starting database and loading Chile election data..."
	docker compose up -d postgres
	@echo "Waiting for database to be ready..."
	sleep 10
	docker compose run --build app python scripts/load_chile_data.py
	@echo "Chile data loaded successfully!"

# Start production stack (requires external database configuration)
prod-deploy:
	az acr run -f ./acr-build-task.yml --registry embackendacr --set image="em/backend:latest" .

# View production application logs
prod-logs:
	az webapp log tail --resource-group em-backend-rg --name em-backend

# Access production container shell
prod-shell:
	az webapp ssh --resource-group em-backend-rg --name em-backend

# Stop all services
down:
	docker compose down
	docker compose -f docker-compose.prod.yml down

# Clean up all containers and volumes
clean:
	docker compose down -v --remove-orphans
	docker compose -f docker-compose.prod.yml down -v --remove-orphans
	docker system prune -f
