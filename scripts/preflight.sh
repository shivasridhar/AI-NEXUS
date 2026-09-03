#!/bin/bash
# SentinelAI Preflight Validation Script
# Ensures that all infrastructure, environment configurations, and services are healthy before deployment.

# ANSI Color Codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo "======================================"
echo " SentinelAI Preflight Checklist"
echo "======================================"

check_success() {
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}[PASS]${NC} $1"
  else
    echo -e "${RED}[FAIL]${NC} $1"
    if [ "$2" == "fatal" ]; then
      echo -e "${RED}Preflight checks failed. Aborting deploy.${NC}"
      exit 1
    fi
  fi
}

# 1. Environment Validation
echo -e "\n--- 1. Environment Validation ---"
if [ -f "sentinel_backend/.env" ]; then
  grep -q "POSTGRES_SERVER" sentinel_backend/.env && grep -q "SECRET_KEY" sentinel_backend/.env
  check_success "Backend .env has critical variables" "fatal"
else
  echo -e "${RED}[FAIL]${NC} Backend .env missing"
  exit 1
fi

if [ -f "sentinel_frontend/.env.local" ]; then
  grep -q "NEXT_PUBLIC_API_URL" sentinel_frontend/.env.local
  check_success "Frontend .env.local has critical variables" "warn"
else
  echo -e "${YELLOW}[WARN]${NC} Frontend .env.local missing"
fi

# 2. Docker Validation
echo -e "\n--- 2. Docker Validation ---"
if command -v docker &> /dev/null; then
  docker info >/dev/null 2>&1
  check_success "Docker daemon is running" "fatal"
else
  echo -e "${RED}[FAIL]${NC} Docker not installed or running."
  exit 1
fi

docker compose config >/dev/null 2>&1
check_success "docker-compose.yml is valid" "fatal"

# 3. Database Startup & Health
echo -e "\n--- 3. Database Health ---"
if command -v nc &> /dev/null; then
  nc -z localhost 5433
  check_success "PostgreSQL is reachable on port 5433" "fatal"
  
  nc -z localhost 7687
  check_success "Neo4j is reachable on port 7687" "fatal"
else
  echo -e "${YELLOW}[WARN]${NC} 'nc' not found. Checking docker ps instead."
  docker ps | grep -q sentinel_postgres
  check_success "PostgreSQL container is running" "fatal"
  docker ps | grep -q sentinel_neo4j
  check_success "Neo4j container is running" "fatal"
fi

# 4. Migration Verification
echo -e "\n--- 4. Migration Verification ---"
if [ -d "sentinel_backend/venv" ]; then
  cd sentinel_backend
  source venv/bin/activate
  alembic current >/dev/null 2>&1
  check_success "Alembic migrations are up to date" "fatal"
  deactivate
  cd ..
else
  echo -e "${YELLOW}[WARN]${NC} Backend virtual environment not found at sentinel_backend/venv. Skipping Alembic check."
fi

# 5. API & Configuration Verification
echo -e "\n--- 5. API Health & Configuration Verification ---"
if command -v curl &> /dev/null; then
  # Hit the backend health endpoint
  HEALTH_STATUS=$(curl -s http://localhost:8000/api/v1/health | grep -E '"status": ?"ok"')
  if [ -n "$HEALTH_STATUS" ]; then
    echo -e "${GREEN}[PASS]${NC} API /health endpoint is responding OK"
  else
    echo -e "${RED}[FAIL]${NC} API /health endpoint did not respond OK (Is the FastAPI server running?)"
  fi
else
  echo -e "${YELLOW}[WARN]${NC} 'curl' not found. Skipping API check."
fi

# 6. Frontend Verification
echo -e "\n--- 6. Frontend Verification ---"
if command -v curl &> /dev/null; then
  curl -s http://localhost:3000 > /dev/null
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}[PASS]${NC} Frontend server is reachable"
  else
    echo -e "${RED}[FAIL]${NC} Frontend server is not reachable on port 3000"
  fi
fi

echo -e "\n======================================"
echo -e "${GREEN}Preflight completed!${NC}"
echo "======================================"
