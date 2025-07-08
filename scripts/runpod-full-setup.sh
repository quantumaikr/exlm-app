#!/bin/bash

# EXLM Platform RunPod 완전 자동 설치 스크립트
# Usage: curl -sSL https://raw.githubusercontent.com/quantumaikr/exlm-app/main/scripts/runpod-full-setup.sh | bash

set -e

echo "🚀 EXLM Platform RunPod 완전 자동 설치 시작..."
echo "================================================="

# 컬러 출력 함수
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 시작 시간 기록
START_TIME=$(date +%s)

# 1. 시스템 환경 확인
print_status "시스템 환경 확인 중..."
echo "현재 사용자: $(whoami)"
echo "현재 디렉토리: $(pwd)"
echo "시스템 정보: $(uname -a)"
echo "Ubuntu 버전: $(lsb_release -d | cut -f2)"

# GPU 확인
if command -v nvidia-smi &> /dev/null; then
    print_success "GPU 감지됨"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits
    GPU_AVAILABLE=true
else
    print_warning "GPU 미감지 - CPU 모드로 설치"
    GPU_AVAILABLE=false
fi

# 2. 시스템 업데이트
print_status "시스템 업데이트 중..."
export DEBIAN_FRONTEND=noninteractive

# apt 업데이트 재시도 로직
for i in {1..3}; do
    if apt update -qq; then
        break
    else
        print_warning "apt update 실패, 재시도 중... ($i/3)"
        sleep 2
    fi
done

# 시스템 업그레이드 (선택사항, 시간이 오래 걸릴 수 있음)
print_status "시스템 업그레이드 중..."
apt upgrade -y -qq || print_warning "시스템 업그레이드 실패, 계속 진행..."

# 3. 필수 의존성 설치
print_status "필수 의존성 설치 중..."
apt install -y -qq \
    git curl wget build-essential software-properties-common \
    ca-certificates gnupg lsb-release apt-transport-https \
    openssl unzip vim nano htop net-tools \
    python3-pip python3-dev python3-venv

# 4. Python 3.11 설치
print_status "Python 3.11 설치 중..."

# apt_pkg 모듈 문제 해결
print_status "apt_pkg 모듈 문제 해결 중..."
# 기존 심볼릭 링크 제거
rm -f /usr/lib/python3/dist-packages/apt_pkg.cpython-*.so 2>/dev/null || true
# 새로운 심볼릭 링크 생성
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
find /usr/lib/python3/dist-packages/ -name "apt_pkg.cpython-*.so" | head -1 | xargs -I {} ln -sf {} /usr/lib/python3/dist-packages/apt_pkg.cpython-${PYTHON_VERSION}*-x86_64-linux-gnu.so 2>/dev/null || true

# PPA 추가 (apt_pkg 문제 해결 후)
if add-apt-repository ppa:deadsnakes/ppa -y; then
    # apt 업데이트
    apt update -qq || print_warning "apt update 실패"
    
    # Python 3.11 설치
    if apt install -y -qq python3.11 python3.11-venv python3.11-dev python3.11-distutils; then
        # Python 3.11을 기본으로 설정
        update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 2>/dev/null || true
        update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3 1 2>/dev/null || true
        print_success "Python 3.11 설치 완료: $(python3 --version)"
    else
        print_warning "Python 3.11 설치 실패, 기본 Python 사용"
        # 기본 Python 버전 확인
        python3 --version || print_error "Python 설치 실패"
    fi
else
    print_warning "PPA 추가 실패, 기본 Python 사용"
    # 기본 Python 버전 확인
    python3 --version || print_error "Python 설치 실패"
fi

# Python 버전 확인 및 pip 업그레이드
print_status "Python 환경 확인 중..."
python3 --version
pip3 --version || print_warning "pip3 설치 필요"

# 5. Node.js 18 설치
print_status "Node.js 18 설치 중..."

# NodeSource 저장소 추가
if curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1; then
    apt update -qq || print_warning "apt update 실패"
    
    if apt install -y -qq nodejs; then
        print_success "Node.js 설치 완료: $(node --version), npm: $(npm --version)"
    else
        print_warning "Node.js 설치 실패, 기본 Node.js 사용"
        # 기본 Node.js 버전 확인
        node --version || print_error "Node.js 설치 실패"
    fi
else
    print_warning "NodeSource 저장소 추가 실패, 기본 Node.js 사용"
    # 기본 Node.js 버전 확인
    node --version || print_error "Node.js 설치 실패"
fi

# 6. PostgreSQL 설치 및 설정
print_status "PostgreSQL 설치 및 설정 중..."

if apt install -y -qq postgresql postgresql-contrib; then
    # PostgreSQL 서비스 시작
    systemctl start postgresql || print_warning "PostgreSQL 서비스 시작 실패"
    systemctl enable postgresql || print_warning "PostgreSQL 서비스 자동 시작 설정 실패"
    
    # 데이터베이스 설정
    print_status "데이터베이스 설정 중..."
    sudo -u postgres psql -c "CREATE USER exlm_user WITH PASSWORD 'exlm_password';" 2>/dev/null || print_warning "사용자 생성 실패 (이미 존재할 수 있음)"
    sudo -u postgres psql -c "CREATE DATABASE exlm_db OWNER exlm_user;" 2>/dev/null || print_warning "데이터베이스 생성 실패 (이미 존재할 수 있음)"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE exlm_db TO exlm_user;" 2>/dev/null || print_warning "권한 부여 실패"
    sudo -u postgres psql -c "ALTER USER exlm_user CREATEDB;" 2>/dev/null || print_warning "사용자 권한 변경 실패"
    
    print_success "PostgreSQL 설정 완료"
else
    print_error "PostgreSQL 설치 실패"
    exit 1
fi

# 7. Redis 설치 및 설정
print_status "Redis 설치 및 설정 중..."

if apt install -y -qq redis-server; then
    # Redis 서비스 시작
    systemctl start redis-server || print_warning "Redis 서비스 시작 실패"
    systemctl enable redis-server || print_warning "Redis 서비스 자동 시작 설정 실패"
    
    print_success "Redis 설정 완료"
else
    print_error "Redis 설치 실패"
    exit 1
fi

# 8. EXLM 프로젝트 클론
print_status "EXLM 프로젝트 클론 중..."
cd /workspace

# 기존 디렉토리 제거 (있다면)
if [ -d "exlm-app" ]; then
    rm -rf exlm-app
fi

git clone https://github.com/quantumaikr/exlm-app.git
cd exlm-app

print_success "프로젝트 클론 완료"

# 9. 백엔드 설정
print_status "백엔드 환경 설정 중..."
cd backend

# Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# pip 업그레이드
pip install --upgrade pip setuptools wheel -q

# GPU/CPU에 따른 requirements 설치
if [ "$GPU_AVAILABLE" = true ]; then
    print_status "GPU requirements 설치 중..."
    
    # PyTorch CUDA 버전 설치
    print_status "PyTorch CUDA 버전 설치 중..."
    pip install torch==2.1.1 torchvision==0.16.1 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu118 -q
    
    # 핵심 의존성 먼저 설치
    print_status "핵심 라이브러리 설치 중..."
    pip install "pydantic==1.10.13" "pydantic-settings==0.2.5" "fastapi==0.100.1" -q
    
    print_status "ML 라이브러리 설치 중..."
    pip install "transformers==4.36.2" "accelerate==0.25.0" "tokenizers==0.15.0" "datasets==2.16.1" -q
    
    # 나머지 GPU requirements 설치
    print_status "GPU 전용 라이브러리 설치 중..."
    pip install -r requirements-gpu.txt -q
else
    print_status "CPU requirements 설치 중..."
    # 핵심 의존성 먼저 설치
    pip install "pydantic==1.10.13" "pydantic-settings==0.2.5" "fastapi==0.100.1" -q
    
    print_status "ML 라이브러리 설치 중..."
    pip install "transformers==4.36.2" "accelerate==0.25.0" "tokenizers==0.15.0" "datasets==2.16.1" -q
    
    # 나머지 requirements 설치
    pip install -r requirements.txt -q
fi

print_success "백엔드 의존성 설치 완료"

# 10. 환경 변수 설정
print_status "환경 변수 설정 중..."
cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql+asyncpg://exlm_user:exlm_password@localhost:5432/exlm_db

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# API Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
BUILD_ENV=$([ "$GPU_AVAILABLE" = true ] && echo "gpu" || echo "dev")
DEBUG=True

# External APIs (나중에 실제 키로 교체하세요)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GOOGLE_API_KEY=your_google_key_here
HF_TOKEN=your_huggingface_token_here

# CORS 설정
CORS_ORIGINS=["http://localhost:3000","https://*.proxy.runpod.net"]
EOF

print_success "환경 변수 설정 완료"

# 11. 데이터베이스 마이그레이션
print_status "데이터베이스 마이그레이션 중..."
source venv/bin/activate
alembic upgrade head

print_success "데이터베이스 마이그레이션 완료"

# 12. 프론트엔드 설정
print_status "프론트엔드 설정 중..."
cd ../frontend

# 의존성 설치
npm install -q

# 환경 변수 설정
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
EOF

# 빌드
npm run build

print_success "프론트엔드 설정 완료"

# 13. 서비스 시작 스크립트 생성
print_status "서비스 관리 스크립트 생성 중..."
cd /workspace/exlm-app

# 로그 디렉토리 생성
mkdir -p logs

# 백엔드 시작 스크립트
cat > start-backend.sh << 'EOF'
#!/bin/bash
echo "🚀 백엔드 시작 중..."
cd /workspace/exlm-app/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
EOF

# 프론트엔드 시작 스크립트
cat > start-frontend.sh << 'EOF'
#!/bin/bash
echo "🎨 프론트엔드 시작 중..."
cd /workspace/exlm-app/frontend
npm run start
EOF

# Celery 워커 시작 스크립트
cat > start-celery.sh << 'EOF'
#!/bin/bash
echo "🔄 Celery 워커 시작 중..."
cd /workspace/exlm-app/backend
source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
EOF

# Flower 시작 스크립트
cat > start-flower.sh << 'EOF'
#!/bin/bash
echo "🌸 Flower 시작 중..."
cd /workspace/exlm-app/backend
source venv/bin/activate
celery -A app.core.celery_app flower --port=5555 --host=0.0.0.0
EOF

# 모든 서비스 시작 스크립트
cat > start-all.sh << 'EOF'
#!/bin/bash
echo "🚀 모든 서비스 시작 중..."

# 기존 프로세스 정리
pkill -f "uvicorn|npm|celery" 2>/dev/null || true
sleep 2

# 백엔드 시작 (백그라운드)
echo "📡 백엔드 시작..."
nohup /workspace/exlm-app/start-backend.sh > /workspace/exlm-app/logs/backend.log 2>&1 &
echo "✅ 백엔드 시작됨"

# 백엔드 시작 대기
sleep 5

# 프론트엔드 시작 (백그라운드)
echo "🎨 프론트엔드 시작..."
nohup /workspace/exlm-app/start-frontend.sh > /workspace/exlm-app/logs/frontend.log 2>&1 &
echo "✅ 프론트엔드 시작됨"

# Celery 워커 시작 (백그라운드)
echo "🔄 Celery 워커 시작..."
nohup /workspace/exlm-app/start-celery.sh > /workspace/exlm-app/logs/celery.log 2>&1 &
echo "✅ Celery 워커 시작됨"

# Flower 시작 (백그라운드)
echo "🌸 Flower 시작..."
nohup /workspace/exlm-app/start-flower.sh > /workspace/exlm-app/logs/flower.log 2>&1 &
echo "✅ Flower 시작됨"

echo ""
echo "🎉 모든 서비스 시작 완료!"
echo ""
echo "📊 서비스 상태 확인 중..."
sleep 5
ps aux | grep -E "(uvicorn|npm|celery)" | grep -v grep

echo ""
echo "🔍 포트 사용 상태:"
netstat -tulpn | grep -E ':(3000|8000|5555)' 2>/dev/null || echo "포트 확인 중..."

echo ""
echo "🌐 접속 정보:"
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
EOF

# 서비스 중지 스크립트
cat > stop-all.sh << 'EOF'
#!/bin/bash
echo "🛑 모든 서비스 중지 중..."

pkill -f "uvicorn" 2>/dev/null && echo "✅ 백엔드 중지됨" || echo "백엔드가 실행 중이지 않음"
pkill -f "npm" 2>/dev/null && echo "✅ 프론트엔드 중지됨" || echo "프론트엔드가 실행 중이지 않음"
pkill -f "celery" 2>/dev/null && echo "✅ Celery 서비스 중지됨" || echo "Celery가 실행 중이지 않음"

echo "✅ 모든 서비스 중지 완료"
EOF

# 상태 확인 스크립트
cat > status.sh << 'EOF'
#!/bin/bash
echo "📊 EXLM 서비스 상태 확인"
echo "=========================="

echo ""
echo "🔍 실행 중인 프로세스:"
ps aux | grep -E "(uvicorn|npm|celery)" | grep -v grep

echo ""
echo "🌐 포트 사용 상태:"
netstat -tulpn | grep -E ':(3000|8000|5555)' 2>/dev/null || echo "서비스가 실행 중이지 않음"

echo ""
echo "💾 시스템 리소스:"
echo "메모리 사용량:"
free -h

echo ""
echo "디스크 사용량:"
df -h /

if command -v nvidia-smi &> /dev/null; then
    echo ""
    echo "🎮 GPU 상태:"
    nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits 2>/dev/null || echo "GPU 정보 확인 실패"
fi

echo ""
echo "🗄️ 데이터베이스 연결:"
sudo -u postgres psql -c "\l" 2>/dev/null | grep exlm_db || echo "데이터베이스 연결 확인 실패"

echo ""
echo "🔴 Redis 연결:"
redis-cli ping 2>/dev/null || echo "Redis 연결 확인 실패"
EOF

# 빠른 재시작 스크립트
cat > restart.sh << 'EOF'
#!/bin/bash
echo "🔄 EXLM 서비스 재시작 중..."
./stop-all.sh
sleep 3
./start-all.sh
EOF

# 실행 권한 부여
chmod +x start-*.sh stop-all.sh status.sh restart.sh

print_success "서비스 관리 스크립트 생성 완료"

# 14. 서비스 시작
print_status "서비스 시작 중..."
./start-all.sh

# 15. 설치 완료 및 정보 출력
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "================================================="
print_success "🎉 EXLM Platform 설치 완료!"
echo "================================================="
echo ""
echo "⏱️  설치 시간: ${DURATION}초"
echo ""
echo "🌐 RunPod 포트 설정:"
echo "RunPod 웹 콘솔에서 다음 포트들을 Public으로 설정하세요:"
echo "- 3000 (Frontend) - 필수"
echo "- 8000 (Backend API) - 필수"
echo "- 5555 (Flower) - 선택사항"
echo ""
echo "🔗 접속 URL (포트 설정 후):"
echo "- Frontend: https://[POD_ID]-3000.proxy.runpod.net"
echo "- Backend API: https://[POD_ID]-8000.proxy.runpod.net"
echo "- API 문서: https://[POD_ID]-8000.proxy.runpod.net/docs"
echo "- Flower: https://[POD_ID]-5555.proxy.runpod.net"
echo ""
echo "🛠️  관리 명령어:"
echo "- 모든 서비스 시작: ./start-all.sh"
echo "- 모든 서비스 중지: ./stop-all.sh"
echo "- 서비스 재시작: ./restart.sh"
echo "- 상태 확인: ./status.sh"
echo ""
echo "📝 로그 확인:"
echo "- 실시간 백엔드 로그: tail -f logs/backend.log"
echo "- 실시간 프론트엔드 로그: tail -f logs/frontend.log"
echo "- 모든 로그: tail -f logs/*.log"
echo ""
echo "🔧 API 키 설정:"
echo "backend/.env 파일을 편집하여 실제 API 키를 입력하세요:"
echo "- OPENAI_API_KEY"
echo "- ANTHROPIC_API_KEY"
echo "- GOOGLE_API_KEY"
echo "- HF_TOKEN"
echo ""
print_success "설치가 완료되었습니다! 🚀" 