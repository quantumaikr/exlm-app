#!/bin/bash

# EXLM Platform Local Setup Script (소스코드가 이미 있는 경우)
# Usage: ./setup-runpod-local.sh

set -e

echo "🚀 EXLM Platform 로컬 설치 시작..."
echo "📁 현재 디렉토리: $(pwd)"

# 현재 디렉토리가 EXLM 프로젝트 루트인지 확인
if [ ! -f "docker-compose.yml" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ EXLM 프로젝트 루트 디렉토리가 아닙니다."
    echo "다음 파일/폴더가 있는 디렉토리에서 실행하세요:"
    echo "- docker-compose.yml"
    echo "- backend/"
    echo "- frontend/"
    echo ""
    echo "올바른 디렉토리로 이동 후 다시 실행하세요:"
    echo "cd /path/to/exlm-app"
    echo "./scripts/setup-runpod-local.sh"
    exit 1
fi

echo "✅ EXLM 프로젝트 디렉토리 확인됨"

# 시스템 업데이트
echo "📦 시스템 업데이트 중..."
apt-get update -qq
apt-get install -y git curl wget build-essential software-properties-common

# Python 3.11 설치
echo "🐍 Python 3.11 설치 중..."
add-apt-repository ppa:deadsnakes/ppa -y
apt-get update
apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Node.js 18 설치
echo "📦 Node.js 18 설치 중..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# PostgreSQL 설치
echo "🐘 PostgreSQL 설치 중..."
apt-get install -y postgresql postgresql-contrib
systemctl start postgresql || service postgresql start

# Redis 설치
echo "🔴 Redis 설치 중..."
apt-get install -y redis-server
systemctl start redis-server || service redis-server start

# 데이터베이스 설정
echo "🗄️ 데이터베이스 설정 중..."
sudo -u postgres psql -c "CREATE USER exlm_user WITH PASSWORD 'exlm_password';" || echo "사용자가 이미 존재합니다."
sudo -u postgres psql -c "CREATE DATABASE exlm_db OWNER exlm_user;" || echo "데이터베이스가 이미 존재합니다."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE exlm_db TO exlm_user;" || echo "권한 설정 완료"

# 백엔드 설정
echo "⚙️ 백엔드 설정 중..."
cd backend

# Python 가상환경 생성
echo "🔧 Python 가상환경 생성 중..."
python3.11 -m venv venv
source venv/bin/activate

# GPU 환경 확인 및 requirements 설치
if command -v nvidia-smi &> /dev/null; then
    echo "✅ GPU 감지됨 - GPU requirements 설치"
    
    # PyTorch CUDA 버전을 먼저 설치
    echo "🔥 PyTorch CUDA 버전 설치 중..."
    pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu118
    
    # GPU requirements 설치 (torch는 이미 주석처리됨)
    echo "📦 GPU requirements 설치 중..."
    pip install -r requirements-gpu.txt
else
    echo "⚠️ GPU 미감지 - CPU requirements 설치"
    pip install -r requirements.txt
fi

# 환경 변수 설정
echo "🔧 환경 변수 설정 중..."
cat > .env << EOF
# Database
DATABASE_URL=postgresql+asyncpg://exlm_user:exlm_password@localhost:5432/exlm_db

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# API Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
BUILD_ENV=gpu
DEBUG=True

# External APIs (선택사항 - 나중에 수정하세요)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here
HF_TOKEN=your_huggingface_token_here
EOF

# 데이터베이스 마이그레이션
echo "🔄 데이터베이스 마이그레이션 중..."
alembic upgrade head

# 프론트엔드 설정
echo "🎨 프론트엔드 설정 중..."
cd ../frontend
npm install
npm run build

# 서비스 시작 스크립트 생성
echo "🚀 서비스 시작 스크립트 생성 중..."
cd ..

# 로그 디렉토리 생성
mkdir -p logs

# 백엔드 시작 스크립트
cat > start-backend.sh << 'EOF'
#!/bin/bash
echo "🚀 백엔드 시작 중..."
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
EOF

# 프론트엔드 시작 스크립트
cat > start-frontend.sh << 'EOF'
#!/bin/bash
echo "🎨 프론트엔드 시작 중..."
cd frontend
npm run start
EOF

# Celery 워커 시작 스크립트
cat > start-celery.sh << 'EOF'
#!/bin/bash
echo "🔄 Celery 워커 시작 중..."
cd backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
EOF

# Celery Flower 시작 스크립트
cat > start-flower.sh << 'EOF'
#!/bin/bash
echo "🌸 Flower 시작 중..."
cd backend
source venv/bin/activate
celery -A app.core.celery_app flower --port=5555
EOF

# 모든 서비스 시작 스크립트
cat > start-all.sh << 'EOF'
#!/bin/bash
echo "🚀 모든 서비스 시작 중..."

# 백엔드 시작 (백그라운드)
nohup ./start-backend.sh > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 백엔드 시작됨 (PID: $BACKEND_PID)"

# 프론트엔드 시작 (백그라운드)
nohup ./start-frontend.sh > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ 프론트엔드 시작됨 (PID: $FRONTEND_PID)"

# Celery 워커 시작 (백그라운드)
nohup ./start-celery.sh > logs/celery.log 2>&1 &
CELERY_PID=$!
echo "✅ Celery 워커 시작됨 (PID: $CELERY_PID)"

# Flower 시작 (백그라운드)
nohup ./start-flower.sh > logs/flower.log 2>&1 &
FLOWER_PID=$!
echo "✅ Flower 시작됨 (PID: $FLOWER_PID)"

echo ""
echo "🎉 모든 서비스가 시작되었습니다!"
echo ""
echo "📊 서비스 상태 확인:"
sleep 5
ps aux | grep -E "(uvicorn|npm|celery)" | grep -v grep
EOF

# 서비스 중지 스크립트
cat > stop-all.sh << 'EOF'
#!/bin/bash
echo "🛑 모든 서비스 중지 중..."

# 프로세스 종료
pkill -f "uvicorn|npm|celery" || echo "실행 중인 서비스가 없습니다."

echo "✅ 모든 서비스가 중지되었습니다."
EOF

# 스크립트 실행 권한 부여
chmod +x start-*.sh stop-all.sh

echo ""
echo "🎉 설치 완료!"
echo ""
echo "🚀 서비스 시작 방법:"
echo "1. 모든 서비스 한 번에 시작: ./start-all.sh"
echo "2. 개별 서비스 시작:"
echo "   - 백엔드: ./start-backend.sh"
echo "   - 프론트엔드: ./start-frontend.sh"
echo "   - Celery: ./start-celery.sh"
echo "   - Flower: ./start-flower.sh"
echo ""
echo "🛑 서비스 중지: ./stop-all.sh"
echo ""
echo "📡 접속 정보:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API 문서: http://localhost:8000/docs"
echo "- Flower: http://localhost:5555"
echo ""
echo "📝 로그 확인:"
echo "- Backend: tail -f logs/backend.log"
echo "- Frontend: tail -f logs/frontend.log"
echo "- Celery: tail -f logs/celery.log"
echo "- Flower: tail -f logs/flower.log"
echo ""
echo "⚠️ RunPod에서 다음 포트들을 Public으로 설정하세요:"
echo "- 3000 (Frontend)"
echo "- 8000 (Backend API)"
echo "- 5555 (Flower - 선택사항)"
echo ""
echo "🔧 API 키 설정:"
echo "backend/.env 파일을 편집하여 실제 API 키를 입력하세요." 