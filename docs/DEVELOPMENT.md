# Development Guide

## Quick Development Setup

The fastest way to start developing ElectOMate-Backend:

```bash
# 1. Clone and setup
git clone https://github.com/ElectOMate/ElectOMate-Backend.git
cd ElectOMate-Backend

# 2. Configure environment  
cp .env.example .env
# Edit .env with your API keys

# 3. Start development stack
make dev

# 4. Access the application
# API: http://localhost:8000
# Database: localhost:5433
```

## Development Workflow

### Daily Development

```bash
# Start the stack
make dev

# View logs in real-time
make dev-logs

# Access container for debugging
make dev-shell

# Stop when done
make down
```

### Database Operations

```bash
# Create a new migration
make migration message="add user table"

# Apply pending migrations
make db-migrate

# Connect to database
docker-compose exec postgres psql -U postgres -d em_dev
```

### Common Tasks

#### Adding New Dependencies

```bash
# Access the container
make dev-shell

# Inside container, add package
uv add package-name

# Exit and rebuild
exit
docker-compose up --build
```

#### Debugging

```bash
# View application logs
make dev-logs

# Access container shell for debugging
make dev-shell

# Check database connection
docker-compose exec app python -c "from em_backend.database import engine; print('DB OK')"
```

#### Resetting Development Environment

```bash
# Complete reset (destroys all data)
make clean
make dev
```

## Environment Variables

Required in `.env` file:

```bash
# Vector Database (Weaviate)
WV_URL=your-weaviate-url
WV_API_KEY=your-weaviate-key

# LLM Services (OpenAI)
OPENAI_API_KEY=your-openai-key

# Application
ENV=dev

# Database (auto-configured for Docker)
POSTGRES_URL=postgresql+psycopg://postgres:postgres@postgres:5432/em_dev
```

## File Structure

```text
ElectOMate-Backend/
├── src/em_backend/           # Main application code
│   ├── routers/             # FastAPI route handlers
│   ├── database/            # Database models and utilities
│   ├── agent/               # AI agent functionality
│   └── main.py              # Application entry point
├── alembic/                 # Database migrations
├── docker/                  # Docker configuration
├── docker-compose.yml       # Main compose configuration
├── docker-compose.override.yml  # Development overrides
└── Makefile                 # Development commands
```

## Tips

- **Hot Reload**: Code changes are automatically reflected
- **Database**: Accessible on localhost:5433 from host
- **API Docs**: Available at <http://localhost:8000/docs>
- **Logs**: Use `make dev-logs` for real-time application logs
- **Shell Access**: Use `make dev-shell` for container debugging
