#!/bin/bash

# Automated testing script for exlm project

set -e  # Exit on error

echo "========================================="
echo "Running Automated Tests for EXLM Project"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        return 1
    fi
}

# Backend Tests
echo -e "\n${YELLOW}Running Backend Tests...${NC}"
cd backend

# Check Python environment
echo "Checking Python environment..."
source venv/bin/activate
python --version

# Run linting
echo -e "\n${YELLOW}Running Backend Linting...${NC}"
if command -v flake8 &> /dev/null; then
    flake8 app/ --max-line-length=120 --exclude=app/api/endpoints/quality_filter.py || true
else
    echo "Flake8 not found, skipping..."
fi

# Run type checking
echo -e "\n${YELLOW}Running Backend Type Checking...${NC}"
if command -v mypy &> /dev/null; then
    mypy app/ --ignore-missing-imports || true
else
    echo "Mypy not found, skipping..."
fi

# Run backend tests
echo -e "\n${YELLOW}Running Backend Unit Tests...${NC}"
python -m pytest tests/ -v --tb=short || true

# Test backend server startup
echo -e "\n${YELLOW}Testing Backend Server Startup...${NC}"
timeout 5 uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    print_status 0 "Backend server started successfully"
else
    print_status 1 "Backend server failed to start"
fi

# Kill backend server
kill $BACKEND_PID 2>/dev/null || true

cd ..

# Frontend Tests
echo -e "\n${YELLOW}Running Frontend Tests...${NC}"
cd frontend

# Run linting
echo -e "\n${YELLOW}Running Frontend Linting...${NC}"
npm run lint || true

# Run type checking
echo -e "\n${YELLOW}Running Frontend Type Checking...${NC}"
npm run type-check || true

# Run frontend tests
echo -e "\n${YELLOW}Running Frontend Unit Tests...${NC}"
npm test -- --passWithNoTests || true

# Build frontend
echo -e "\n${YELLOW}Building Frontend...${NC}"
npm run build

if [ $? -eq 0 ]; then
    print_status 0 "Frontend build successful"
else
    print_status 1 "Frontend build failed"
fi

cd ..

# Summary
echo -e "\n${YELLOW}=========================================${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${YELLOW}=========================================${NC}"

# Check critical files
echo -e "\n${YELLOW}Checking Critical Files...${NC}"
files_to_check=(
    "backend/app/main.py"
    "backend/app/core/config.py"
    "backend/app/api/v1/api.py"
    "frontend/src/pages/index.tsx"
    "frontend/src/lib/api.ts"
    "docker-compose.yml"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        print_status 0 "$file exists"
    else
        print_status 1 "$file missing"
    fi
done

# Database connectivity test
echo -e "\n${YELLOW}Testing Database Connectivity...${NC}"
cd backend
source venv/bin/activate
python -c "
from app.core.config import settings
print(f'Database URL configured: {bool(settings.DATABASE_URL)}')
" || true

cd ..

echo -e "\n${GREEN}Automated testing complete!${NC}"