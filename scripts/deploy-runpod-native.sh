#!/bin/bash

# EXLM Platform RunPod Native Deployment Script (without Docker)
# Usage: ./deploy-runpod-native.sh [TOKEN]

set -e

echo "🚀 EXLM Platform RunPod 네이티브 배포 시작..."

# GitHub Personal Access Token 확인 (선택사항)
if [ -z "$1" ]; then
    echo "⚠️ GitHub Personal Access Token이 제공되지 않았습니다."
    echo "Public 저장소인 경우 토큰 없이도 진행 가능합니다."
    echo ""
    echo "GitHub Token이 필요한 경우:"
    echo "1. GitHub → Settings → Developer settings → Personal access tokens"
    echo "2. 'Generate new token' 클릭"
    echo "3. 권한: repo, read:org 선택"
    echo ""
    echo "사용법: ./deploy-runpod-native.sh YOUR_GITHUB_TOKEN"
    echo ""
    read -p "토큰 없이 계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    REPO_URL="https://github.com/quantumaikr/exlm-app.git"
    echo "📥 Public 저장소로 클론을 시도합니다..."
else
    GITHUB_TOKEN=$1
    REPO_URL="https://${GITHUB_TOKEN}@github.com/quantumaikr/exlm-app.git"
    echo "📥 인증된 접근으로 저장소를 클론합니다..."
fi

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

# 저장소 클론
echo "📥 저장소 클론 중..."
if [ -d "exlm-app" ]; then
    rm -rf exlm-app
fi

# 저장소 클론 시도
if git clone $REPO_URL; then
    echo "✅ 저장소 클론 성공"
    cd exlm-app
else
    echo "❌ 저장소 클론 실패"
    echo "가능한 원인:"
    echo "1. 저장소가 Private이고 토큰이 필요함"
    echo "2. 토큰 권한이 부족함"
    echo "3. 네트워크 연결 문제"
    echo ""
    echo "해결 방법:"
    echo "1. GitHub Personal Access Token 생성"
    echo "2. 스크립트 재실행: ./deploy-runpod-native.sh YOUR_TOKEN"
    exit 1
fi

# 데이터베이스 설정
echo "🗄️ 데이터베이스 설정 중..."
sudo -u postgres psql -c "CREATE USER exlm_user WITH PASSWORD 'exlm_password';" || echo "사용자가 이미 존재합니다."
sudo -u postgres psql -c "CREATE DATABASE exlm_db OWNER exlm_user;" || echo "데이터베이스가 이미 존재합니다."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE exlm_db TO exlm_user;" || echo "권한 설정 완료"

# 백엔드 설정
echo "⚙️ 백엔드 설정 중..."
cd backend

# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# GPU 환경 확인 및 requirements 설치
if command -v nvidia-smi &> /dev/null; then
    echo "✅ GPU 감지됨 - GPU requirements 설치"
    pip install -r requirements-gpu.txt
else
    echo "⚠️ GPU 미감지 - CPU requirements 설치"
    pip install -r requirements.txt
fi

# 환경 변수 설정
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

# External APIs (선택사항)
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

# 백엔드 시작 스크립트
cat > start-backend.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
EOF

# 프론트엔드 시작 스크립트
cat > start-frontend.sh << 'EOF'
#!/bin/bash
cd frontend
npm run start
EOF

# Celery 워커 시작 스크립트
cat > start-celery.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
EOF

# Celery Flower 시작 스크립트
cat > start-flower.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
celery -A app.core.celery_app flower --port=5555
EOF

# 스크립트 실행 권한 부여
chmod +x start-*.sh

# 로그 디렉토리 생성
mkdir -p logs

# 서비스 시작
echo "🚀 서비스 시작 중..."

# 백엔드 시작 (백그라운드)
nohup ./start-backend.sh > logs/backend.log 2>&1 &
echo "✅ 백엔드 시작됨 (PID: $!)"

# 프론트엔드 시작 (백그라운드)
nohup ./start-frontend.sh > logs/frontend.log 2>&1 &
echo "✅ 프론트엔드 시작됨 (PID: $!)"

# Celery 워커 시작 (백그라운드)
nohup ./start-celery.sh > logs/celery.log 2>&1 &
echo "✅ Celery 워커 시작됨 (PID: $!)"

# Flower 시작 (백그라운드)
nohup ./start-flower.sh > logs/flower.log 2>&1 &
echo "✅ Flower 시작됨 (PID: $!)"

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 10

echo "📊 서비스 상태 확인 중..."
ps aux | grep -E "(uvicorn|npm|celery)" | grep -v grep

# 포트 확인
echo "🔍 포트 사용 상태 확인 중..."
netstat -tulpn | grep -E ':(3000|8000|5555)'

echo ""
echo "🎉 배포 완료!"
echo ""
echo "📡 접속 정보:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API 문서: http://localhost:8000/docs"
echo "- Flower (Celery): http://localhost:5555"
echo ""
echo "📝 로그 파일:"
echo "- Backend: logs/backend.log"
echo "- Frontend: logs/frontend.log"
echo "- Celery: logs/celery.log"
echo "- Flower: logs/flower.log"
echo ""
echo "🔧 관리 명령어:"
echo "- 프로세스 확인: ps aux | grep -E '(uvicorn|npm|celery)'"
echo "- 로그 확인: tail -f logs/backend.log"
echo "- 서비스 중지: pkill -f 'uvicorn|npm|celery'"
echo ""
echo "⚠️ RunPod에서 다음 포트들을 Public으로 설정하세요:"
echo "- 3000 (Frontend)"
echo "- 8000 (Backend API)"
echo "- 5555 (Flower - 선택사항)" 