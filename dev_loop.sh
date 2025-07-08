#!/bin/bash

# Automated Development Loop for EXLM Project
# This script runs continuous development checks and provides feedback

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Function to run command and check result
run_check() {
    description=$1
    command=$2
    
    print_color "$BLUE" "\n🔍 $description..."
    if eval "$command"; then
        print_color "$GREEN" "✅ $description - PASSED"
        return 0
    else
        print_color "$RED" "❌ $description - FAILED"
        return 1
    fi
}

# Main loop
while true; do
    clear
    print_color "$YELLOW" "========================================="
    print_color "$YELLOW" "🔄 EXLM Development Loop - $(date)"
    print_color "$YELLOW" "========================================="
    
    # Backend checks
    print_color "$YELLOW" "\n📦 BACKEND CHECKS"
    cd backend
    
    # Python syntax check
    run_check "Python Syntax Check" "python -m py_compile app/**/*.py 2>/dev/null" || true
    
    # Import check
    run_check "Import Check" "python -c 'from app.main import app' 2>/dev/null" || true
    
    # Database connection
    run_check "Database Configuration" "python -c 'from app.core.config import settings; print(f\"DB: {bool(settings.DATABASE_URL)}\")' 2>/dev/null" || true
    
    # API startup test
    print_color "$BLUE" "\n🔍 API Startup Test..."
    timeout 5 bash -c "source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000" >/dev/null 2>&1 &
    API_PID=$!
    sleep 3
    
    if curl -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
        print_color "$GREEN" "✅ API Startup - PASSED"
        curl -s http://localhost:8000/api/v1/health | jq . 2>/dev/null || true
    else
        print_color "$RED" "❌ API Startup - FAILED"
    fi
    
    kill $API_PID 2>/dev/null || true
    
    cd ..
    
    # Frontend checks
    print_color "$YELLOW" "\n📦 FRONTEND CHECKS"
    cd frontend
    
    # TypeScript check
    run_check "TypeScript Compilation" "npx tsc --noEmit 2>/dev/null" || true
    
    # Build check
    print_color "$BLUE" "\n🔍 Frontend Build Check..."
    if npm run build >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Frontend Build - PASSED"
    else
        print_color "$RED" "❌ Frontend Build - FAILED"
    fi
    
    cd ..
    
    # Summary
    print_color "$YELLOW" "\n📊 SUMMARY"
    
    # Count issues
    backend_issues=$(cd backend && flake8 app/ --count --exit-zero 2>/dev/null || echo "0")
    print_color "$BLUE" "Backend lint issues: $backend_issues"
    
    # File counts
    py_files=$(find backend/app -name "*.py" | wc -l)
    tsx_files=$(find frontend/src -name "*.tsx" | wc -l)
    print_color "$BLUE" "Python files: $py_files"
    print_color "$BLUE" "TypeScript files: $tsx_files"
    
    # Progress check
    completed_tasks=$(grep -c "\[x\]" docs/WBS.md 2>/dev/null || echo "0")
    total_tasks=$(grep -c "\[\s\]\\|\[x\]" docs/WBS.md 2>/dev/null || echo "0")
    if [ $total_tasks -gt 0 ]; then
        progress=$((completed_tasks * 100 / total_tasks))
        print_color "$BLUE" "WBS Progress: $completed_tasks/$total_tasks ($progress%)"
    fi
    
    print_color "$YELLOW" "\n========================================="
    print_color "$GREEN" "Press Ctrl+C to stop, or wait 30s for next cycle..."
    
    # Wait for 30 seconds or until interrupted
    sleep 30
done