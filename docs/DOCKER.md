# Docker Setup Documentation

## Overview

The Dockerfile has been configured with an entrypoint script that:

1. **Validates Environment Variables**: Checks that all required environment variables from `.env` are available
2. **Runs Database Migrations**: Executes `alembic upgrade head` before starting the application
3. **Provides Clear Feedback**: Uses colored output to show the status of each step

## Required Environment Variables

The following environment variables must be set (from `.env`):

- `WV_URL`: Weaviate database URL
- `WV_API_KEY`: Weaviate API key
- `POSTGRES_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for LLM operations
- `ENV`: Environment (dev/prod)

## Usage

### Development with Docker Compose

```bash
# Make sure your .env file is properly configured
docker-compose up --build
```

### Production Build

```bash
# Build the image
docker build -t electromate-backend .

# Run with environment variables
docker run --env-file .env -p 8000:8000 electromate-backend
```

## Entrypoint Behavior

The entrypoint script (`/entrypoint.sh`) will:

1. 🚀 Display startup message
2. 📋 Check all required environment variables
3. ✅ Confirm all variables are present (or exit with error)
4. 🔄 Run Alembic database migrations
5. ✅ Confirm migrations completed successfully
6. 🎯 Start the FastAPI application

If any step fails, the container will exit with a non-zero status code and display clear error messages.

## Security Features

- Runs as non-root user (`app:app`)
- Minimal system dependencies
- Multi-stage build for smaller final image
