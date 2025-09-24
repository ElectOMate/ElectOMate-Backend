#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting ElectOMate Backend...${NC}"

# List of required environment variables from .env file
REQUIRED_VARS=(
    "WV_URL"
    "WV_API_KEY"
    "POSTGRES_URL"
    "OPENAI_API_KEY"
)

echo -e "${YELLOW}📋 Checking environment variables...${NC}"

# Check if all required environment variables are set
missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    else
        echo -e "${GREEN}✓${NC} $var is set"
    fi
done

# If any variables are missing, exit with error
if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ Error: The following required environment variables are missing:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}  - $var${NC}"
    done
    echo -e "${RED}Please ensure all environment variables from .env are properly set.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All environment variables are present${NC}"

# Run Alembic migrations
echo -e "${YELLOW}🔄 Running database migrations...${NC}"
if alembic upgrade head; then
    echo -e "${GREEN}✅ Database migrations completed successfully${NC}"
else
    echo -e "${RED}❌ Database migrations failed${NC}"
    exit 1
fi

# Execute the main command
echo -e "${GREEN}🎯 Starting application...${NC}"
exec "$@"