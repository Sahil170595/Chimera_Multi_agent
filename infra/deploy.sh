#!/bin/bash
# Deployment script for Muse Protocol orchestrator

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Muse Protocol Deployment ===${NC}"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}" >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo -e "${RED}Docker Compose is required but not installed.${NC}" >&2; exit 1; }

# Load environment
if [ -f "env.local" ]; then
    echo -e "${GREEN}Loading environment from env.local${NC}"
    export $(grep -v '^#' env.local | xargs)
else
    echo -e "${RED}env.local not found!${NC}"
    exit 1
fi

# Build image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -f infra/Dockerfile.orchestrator -t muse-orchestrator:latest .

# Run tests (optional)
if [ "$SKIP_TESTS" != "true" ]; then
    echo -e "\n${YELLOW}Running tests...${NC}"
    docker run --rm muse-orchestrator:latest pytest tests/ || {
        echo -e "${RED}Tests failed!${NC}"
        exit 1
    }
fi

# Stop existing containers
echo -e "\n${YELLOW}Stopping existing containers...${NC}"
docker-compose -f infra/docker-compose.prod.yml down || true

# Start new containers
echo -e "\n${YELLOW}Starting orchestrator...${NC}"
docker-compose -f infra/docker-compose.prod.yml up -d

# Wait for health check
echo -e "\n${YELLOW}Waiting for health check...${NC}"
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Orchestrator is healthy${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Health check failed${NC}"
        docker-compose -f infra/docker-compose.prod.yml logs
        exit 1
    fi
    echo -n "."
    sleep 2
done

# Check readiness
echo -e "\n${YELLOW}Checking readiness...${NC}"
curl -s http://localhost:8000/ready | python3 -m json.tool || true

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "Orchestrator is running at http://localhost:8000"
echo -e "View logs: docker-compose -f infra/docker-compose.prod.yml logs -f"
echo -e "Stop: docker-compose -f infra/docker-compose.prod.yml down"
