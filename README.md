# ElectOMate-Backend

This repository contains the backend code for the ElectOMate project. The backend is built using Python and provides various functionalities related to election data management and processing.

## Table of Contents

- [Docker Development](#docker-development)
- [Production Deployment](#production-deployment)
- [Available Commands](#available-commands)

## Docker Development

All development for ElectOMate-Backend happens through Docker Compose, which provides a consistent environment and handles all dependencies automatically.

### Prerequisites

- [Docker](https://docs.docker.com/get-started/introduction/get-docker-desktop/) and Docker Compose installed

### Quick Start

1. **Clone the repository:**

    ```bash
    git clone https://github.com/ElectOMate/ElectOMate-Backend.git
    cd ElectOMate-Backend
    ```

2. **Setup environment variables:**

    ```bash
    cp .env.example .env
    # Edit .env with your API keys (Weaviate, OpenAI)
    ```

3. **Start the development stack:**

    ```bash
    make dev
    # or: docker-compose up --build
    ```

4. **Access the application:**
    - **API**: <http://localhost:8000>
    - **Database**: localhost:5433 (from host)
    - **API Docs**: <http://localhost:8000/docs>

### Development Workflow

- **View logs**: `make dev-logs`
- **Access container shell**: `make dev-shell`
- **Create migrations**: `make migration message="your change"`
- **Run migrations**: `make db-migrate`
- **Stop services**: `make down`

## Production Deployment

Production deployments use external PostgreSQL databases only (no containerized database).
Supports managed databases like AWS RDS, Azure Database, Google Cloud SQL, etc.

### Setup External Database

1. **Configure environment variables:**

    ```bash
    cp .env.example .env
    # Edit .env with your database configuration
    ```

2. **Required environment variables for production:**

    ```bash
    POSTGRES_HOST=your-database-host.amazonaws.com
    POSTGRES_PORT=5432
    POSTGRES_DB=em_prod
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=your-secure-password
    ```

    ```bash
    make prod
    # or: docker compose -f docker-compose.prod.yml up --build -d
    ```

### Manual Container Deployment

1. **Build the container:**

    ```bash
    docker build -t em/backend .
    ```

2. **Run with external database:**

    ```bash
    docker run --env-file ./.env -p 8000:8000 em/backend
    ```

## Available Commands

All commands are available via Makefile for easy development:

### Development Commands

- `make dev` - Start full development stack
- `make dev-logs` - View application logs
- `make dev-shell` - Access development container shell
- `make down` - Stop all services

### Database Commands

- `make db-migrate` - Run database migrations
- `make migration message="description"` - Create new migration

### Production Commands

- `make prod` - Start production stack
- `make clean` - Clean up containers and volumes

### Development Features

#### Hot Reload

The development setup includes:

- ✅ Source code hot reload
- ✅ Automatic database migrations on startup
- ✅ Development database with proper extensions
- ✅ Comprehensive logging and debugging

#### Database Access

```bash
# Connect to development database
docker-compose exec postgres psql -U postgres -d em_dev

# Or from host (when postgres port is exposed)
psql -h localhost -p 5433 -U postgres -d em_dev
```

#### Environment Variables

The application requires these environment variables:

- `WV_URL` - Weaviate vector database URL
- `WV_API_KEY` - Weaviate API key
- `OPENAI_API_KEY` - OpenAI API key for LLM services
- `ENV` - Environment (dev/production)
- `POSTGRES_URL` - Database connection string (auto-configured in Docker)

## Architecture

The backend provides:

- **FastAPI REST API** with automatic OpenAPI documentation
- **PostgreSQL database** with Alembic migrations
- **Vector search** via Weaviate integration
- **LLM integration** with OpenAI for intelligent responses
- **Document processing** with automatic chunking and embedding
- **Real-time capabilities** with WebSocket support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Use `make dev` for development
4. Run tests and ensure migrations work
5. Submit a pull request

For detailed development setup, see the Docker Development section above.
