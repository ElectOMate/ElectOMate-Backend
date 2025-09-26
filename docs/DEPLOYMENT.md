# ElectOMate Backend Deployment Guide

This document provides comprehensive deployment instructions for the ElectOMate Backend application, covering both development and production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Production Deployment](#production-deployment)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
- [Common Commands](#common-commands)

## Prerequisites

### Required Software

- Docker and Docker Compose
- Azure CLI (for production deployment)
- Make (for using Makefile commands)

### Environment Variables

Ensure the following environment variables are set (typically in a `.env` file):

- `WV_URL` - Web Vector service URL
- `WV_API_KEY` - Web Vector API key
- `POSTGRES_URL` - PostgreSQL database connection string
- `OPENAI_API_KEY` - OpenAI API key for LLM functionality

## Production Deployment

### Azure Container Registry Deployment

The production deployment uses Azure Container Registry (ACR) and Azure App Service.

#### Deploy to Production

```bash
make prod-deploy
```

This command:

- Builds the Docker image using Azure Container Registry
- Uses the build task configuration from `acr-build-task.yml`
- Tags the image as `em/backend:latest`
- Deploys to the configured Azure App Service

### Production Configuration

The production environment requires:

- External PostgreSQL database (not containerized)
- Proper environment variables configured in Azure App Service
- SSL/TLS certificates for HTTPS
- Monitoring and logging configured

### Production Commands

#### View Production Logs

```bash
make prod-logs
```

Streams logs from the Azure App Service using Azure CLI.

#### Access Production Container

```bash
make prod-shell
```

Opens an SSH session to the production container running in Azure App Service.

## Monitoring and Troubleshooting

### Production Troubleshooting

1. **Check application status:**

   ```bash
   make prod-logs
   ```

2. **Access production environment:**

   ```bash
   make prod-shell
   ```

3. **Monitor Azure resources:**
   - Use Azure Portal to monitor App Service metrics
   - Check Application Insights for detailed telemetry
   - Monitor database performance and connections

## Common Commands

### Makefile Commands Summary

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make dev` | Start development stack with hot reload |
| `make dev-logs` | View development application logs |
| `make dev-shell` | Access development container shell |
| `make db-migrate` | Run database migrations in development |
| `make migration` | Create new migration (requires message parameter) |
| `make prod-deploy` | Deploy to Azure production environment |
| `make prod-logs` | View production application logs |
| `make prod-shell` | Access production container shell |
| `make down` | Stop all services |
| `make clean` | Clean up containers and volumes |

### Docker Compose Files

The project uses multiple Docker Compose configurations:

- `docker-compose.yml` - Base configuration

## Security Considerations

### Development

- Development database is containerized and isolated
- Application runs with non-root user inside container
- SSH access available for debugging (port 2222)

### Production

- Uses managed Azure services for enhanced security
- Environment variables stored securely in Azure App Service
- SSL/TLS termination handled by Azure App Service
- Database connections encrypted
- Container runs with minimal privileges

## Performance Optimization

### Development Performance Optimization

- Use Docker BuildKit for faster builds
- Mount source code for hot reloading
- Local caching for dependencies

### Production Performance Optimization

- Multi-stage Docker builds for smaller images
- Bytecode compilation enabled
- Connection pooling for database
- Structured logging for observability

## Backup and Recovery

### Production Backup and Recovery

- Database backups managed by Azure Database service
- Container images stored in Azure Container Registry
- Application state is stateless for easy recovery

## Support and Maintenance

For issues and maintenance:

1. Check logs using the appropriate log commands
2. Verify environment configuration
3. Ensure all required services are running
4. Review recent deployments and changes
